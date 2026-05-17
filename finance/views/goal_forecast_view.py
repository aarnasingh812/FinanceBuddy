from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from finance.models import MLResult


class GoalForecastView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Read from MLResult (precomputed via POST /ml/compute)
        ml_result = MLResult.objects.filter(
            user=user, feature='forecast', status=True
        ).first()

        if ml_result is None:
            return Response({
                "status": "success",
                "message": "No results found. Click 'Analyse' to compute ML features.",
                "savings_summary": None,
                "allocation_plan": None,
                "forecasts": None,
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "success",
            "computed_at": ml_result.computed_at,
            **ml_result.result,
        }, status=status.HTTP_200_OK)
