from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from finance.models import MLResult
from serializers.recommendation_serializers import RecommendationResponseSerializer


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Read from MLResult (precomputed via POST /ml/compute)
        ml_result = MLResult.objects.filter(
            user=user, feature='recommendation'
        ).order_by('-computed_at').first()

        if ml_result is None:
            response_data = {
                "status": "success",
                "message": "No results found. Click 'Refresh' on the Insights page to compute ML features.",
                "computed_at": None,
                "savings_opportunities": None,
                "spend_optimization": None,
                "goal_insights": None,
                "llm_insights": None,
            }
        else:
            response_data = {
                "status": "success",
                "computed_at": ml_result.computed_at,
                **ml_result.result,
            }

        return Response(
            RecommendationResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
