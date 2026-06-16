from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from celery.result import AsyncResult

from serializers.ml_compute_serializers import MLComputeStatusSerializer


class MLComputeStatusView(APIView):
    """
    GET /api/ml/compute/status/<task_id>

    Polls the status of a background ML compute task.

    Response states:
        PENDING  — task is queued, not yet picked up by a worker
        STARTED  — task is currently running
        SUCCESS  — task completed successfully (result included)
        FAILURE  — task failed (error message included)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id, *args, **kwargs):
        result = AsyncResult(task_id)

        response_data = {
            "task_id": task_id,
            "state": result.state,
            "result": None,
            "error": None,
        }

        if result.state == "SUCCESS":
            response_data["result"] = result.result
        elif result.state == "FAILURE":
            response_data["error"] = str(result.result)

        return Response(MLComputeStatusSerializer(response_data).data)
