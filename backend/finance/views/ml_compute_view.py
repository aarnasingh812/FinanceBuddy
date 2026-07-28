from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle

from serializers.ml_compute_serializers import MLComputeAcceptedSerializer


class MLComputeThrottle(UserRateThrottle):
    """
    Tight per-user rate limit for the expensive ML compute endpoint.
    Rate is configured in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['ml_compute'].
    """
    scope = 'ml_compute'


class MLComputeView(APIView):
    """
    POST /api/ml/compute

    Dispatches all ML feature computations to a Celery background task
    and returns immediately with a task_id for status polling.

    Guards:
    - MLComputeThrottle: max 6 dispatches per user per hour (prevents spam).
    - Idempotency check: if the user's previous task is still PENDING or
      STARTED, the existing task_id is returned and no new job is queued.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [MLComputeThrottle]

    def post(self, request, *args, **kwargs):
        from celery.result import AsyncResult
        from finance.tasks import run_ml_compute
        from finance.models import MLResult

        # ------------------------------------------------------------------
        # Idempotency guard — look up the most recently recorded task_id for
        # this user and check whether that Celery task is still active.
        # ------------------------------------------------------------------
        last_result = (
            MLResult.objects
            .filter(user=request.user, feature='task_id')
            .order_by('-created_at')
            .first()
        )

        if last_result:
            existing_task_id = last_result.result.get('task_id')
            if existing_task_id:
                async_result = AsyncResult(existing_task_id)
                if async_result.state in ('PENDING', 'STARTED'):
                    return Response(
                        MLComputeAcceptedSerializer({
                            "status": "already_running",
                            "message": (
                                "An ML computation is already in progress. "
                                "Poll the existing task for results."
                            ),
                            "task_id": existing_task_id,
                        }).data,
                        status=status.HTTP_202_ACCEPTED,
                    )

        # ------------------------------------------------------------------
        # Dispatch a new task and record its ID so the next POST can check it.
        # ------------------------------------------------------------------
        task = run_ml_compute.delay(request.user.id)

        MLResult.objects.create(
            user=request.user,
            feature='task_id',
            result={'task_id': task.id},
        )

        return Response(
            MLComputeAcceptedSerializer({
                "status": "accepted",
                "message": "ML computation started in background.",
                "task_id": task.id,
            }).data,
            status=status.HTTP_202_ACCEPTED,
        )
