from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from finance.models import AnomalousTransaction, MLResult
from serializers.anomaly_serializers import (
    AnomalyResponseSerializer,
    AnomalyUpdateSerializer,
    AnomalyUpdateResponseSerializer,
)


class AnomalyDetectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Read from MLResult (precomputed via POST /ml/compute)
        ml_result = MLResult.objects.filter(
            user=user, feature='anomaly', status=True
        ).first()

        if ml_result is None:
            response_data = {
                "status": "success",
                "message": "No results found. Click 'Refresh' on the Insights page to compute ML features.",
                "computed_at": None,
                "anomalies": None,
            }
        else:
            response_data = {
                "status": "success",
                "computed_at": ml_result.computed_at,
                "anomalies": ml_result.result.get("anomalies"),
            }

        return Response(
            AnomalyResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        serializer = AnomalyUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        anomaly_id = serializer.validated_data["id"]
        is_dismissed = serializer.validated_data["is_dismissed"]

        try:
            anomaly = AnomalousTransaction.objects.get(
                id=anomaly_id, user=request.user
            )
        except AnomalousTransaction.DoesNotExist:
            return Response(
                {"error": "Anomalous transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        anomaly.is_dismissed = bool(is_dismissed)
        anomaly.save()

        response_data = {
            "status": "success",
            "message": f"Anomaly {'dismissed' if anomaly.is_dismissed else 'restored'} successfully.",
        }
        return Response(
            AnomalyUpdateResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
