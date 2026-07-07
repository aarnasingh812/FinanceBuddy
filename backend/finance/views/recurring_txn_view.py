from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from finance.models import RecurringTransaction, MLResult
from serializers.recurring_serializers import (
    RecurringTransactionResponseSerializer,
    RecurringUpdateSerializer,
    RecurringUpdateResponseSerializer,
)


class RecurringTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Read from MLResult (precomputed via POST /ml/compute)
        ml_result = MLResult.objects.filter(
            user=user, feature='recurring', status=True
        ).first()

        if ml_result is None:
            response_data = {
                "status": "success",
                "message": "No results found. Click 'Refresh' on the Insights page to compute ML features.",
                "computed_at": None,
                "recurring_transactions": None,
            }
        else:
            response_data = {
                "status": "success",
                "computed_at": ml_result.computed_at,
                "recurring_transactions": ml_result.result.get("recurring_transactions"),
            }

        return Response(
            RecurringTransactionResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, *args, **kwargs):
        serializer = RecurringUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        recurring_id = serializer.validated_data["id"]
        is_active = serializer.validated_data["is_active"]

        try:
            recurring = RecurringTransaction.objects.get(id=recurring_id, user=request.user)
        except RecurringTransaction.DoesNotExist:
            return Response(
                {"error": "Recurring transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        recurring.is_active = bool(is_active)
        recurring.save()

        response_data = {
            "status": "success",
            "message": f"Recurring transaction {'activated' if recurring.is_active else 'dismissed'} successfully.",
        }
        return Response(RecurringUpdateResponseSerializer(response_data).data, status=status.HTTP_200_OK)
