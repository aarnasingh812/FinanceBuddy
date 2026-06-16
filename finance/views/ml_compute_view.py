from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from serializers.ml_compute_serializers import MLComputeAcceptedSerializer


class MLComputeView(APIView):
    """
    POST /api/ml/compute

    Dispatches all ML feature computations to a Celery background task
    and returns immediately with a task_id for status polling.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from finance.tasks import run_ml_compute

        task = run_ml_compute.delay(request.user.id)

        return Response(
            MLComputeAcceptedSerializer({
                "status": "accepted",
                "message": "ML computation started in background.",
                "task_id": task.id,
            }).data,
            status=status.HTTP_202_ACCEPTED,
        )
