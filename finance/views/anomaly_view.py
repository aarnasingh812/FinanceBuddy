from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from finance.models import AnomalousTransaction, MLResult


class AnomalyDetectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Read from MLResult (precomputed via POST /ml/compute)
        ml_result = MLResult.objects.filter(
            user=user, feature='anomaly', status=True
        ).first()

        if ml_result is None:
            return Response({
                "status": "success",
                "message": "No results found. Click 'Analyse' to compute ML features.",
                "anomalies": None,
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "success",
            "computed_at": ml_result.computed_at,
            **ml_result.result,
        }, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        anomaly_id = request.data.get("id")
        is_dismissed = request.data.get("is_dismissed")

        if anomaly_id is None or is_dismissed is None:
            return Response(
                {"error": "Both 'id' and 'is_dismissed' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        return Response({
            "status": "success",
            "message": f"Anomaly {'dismissed' if anomaly.is_dismissed else 'restored'} successfully.",
        }, status=status.HTTP_200_OK)
