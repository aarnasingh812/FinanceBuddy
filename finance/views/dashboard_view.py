from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from finance.models import Transaction, Goal
from serializers.dashboard_serializers import (
    DashboardQuerySerializer,
    DashboardTransactionSerializer,
    DashboardGoalSerializer,
    DashboardUserSerializer,
    DashboardResponseSerializer,
)


class DashboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        # --- Validate query params ---
        query_serializer = DashboardQuerySerializer(data=request.GET)
        if not query_serializer.is_valid():
            return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        today = timezone.now()

        # --- Month filter ---
        month_year = query_serializer.validated_data.get("month_year")
        if month_year:
            year, month = map(int, month_year.split("-"))
        else:
            year = today.year
            month = today.month

        # --- Fetch data ---
        transactions = Transaction.objects.filter(
            user=user,
            date__year=year,
            date__month=month,
        ).order_by("-date")

        goals = Goal.objects.filter(user=user).order_by("deadline")

        # --- Compute financial summary for the selected month ---
        total_income = sum(
            float(t.amount) for t in transactions if t.transaction_type == "Income"
        )
        total_expense = sum(
            float(t.amount) for t in transactions if t.transaction_type == "Expense"
        )
        net_savings = round(total_income - total_expense, 2)

        # --- Serialize and return ---
        response_data = {
            "status": "success",
            "message": "Dashboard data fetched successfully.",
            "month": f"{year}-{month:02d}",
            "user": DashboardUserSerializer(user).data,
            "transactions": DashboardTransactionSerializer(transactions, many=True).data,
            "goals": DashboardGoalSerializer(goals, many=True).data,
            "summary": {
                "total_income": round(total_income, 2),
                "total_expense": round(total_expense, 2),
                "net_savings": net_savings,
            },
        }
        return Response(
            DashboardResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )

