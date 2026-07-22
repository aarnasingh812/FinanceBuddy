import copy
import datetime
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from finance.models import MLResult, Transaction
from serializers.recommendation_serializers import RecommendationResponseSerializer


def _compute_avg_income_expense(user):
    """
    Compute average monthly income and expense from the DB.

    Rules:
      - Exclude the current (in-progress) month.
      - Use up to the last 12 complete months of data.
      - If the user has fewer than 12 months of history, use whatever is available.

    Returns:
        (avg_monthly_income: float, avg_monthly_expense: float)
    """
    today = timezone.now().date()

    # Last day of the previous (most recent complete) month
    last_complete_month_end = datetime.date(today.year, today.month, 1) - datetime.timedelta(days=1)

    # First day of the window: 12 months back from the start of the current month
    window_start = datetime.date(today.year - 1, today.month, 1)

    txns = (
        Transaction.objects
        .filter(
            user=user,
            date__gte=window_start,
            date__lte=last_complete_month_end,
        )
        .values("amount", "date", "transaction_type")
    )

    if not txns:
        return 0.0, 0.0

    income_by_month: dict = defaultdict(Decimal)
    expense_by_month: dict = defaultdict(Decimal)

    for t in txns:
        ym = (t["date"].year, t["date"].month)
        if t["transaction_type"] == "Income":
            income_by_month[ym] += t["amount"]
        else:
            expense_by_month[ym] += t["amount"]

    # Union of all months that had any transaction
    all_months = set(income_by_month) | set(expense_by_month)
    if not all_months:
        return 0.0, 0.0

    n = len(all_months)
    avg_income = float(sum(income_by_month.values()) / n)
    avg_expense = float(sum(expense_by_month.values()) / n)

    return round(avg_income, 2), round(avg_expense, 2)


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # ── Compute live averages from DB (last ≤12 complete months) ──
        avg_income, avg_expense = _compute_avg_income_expense(user)

        # ── Read pre-computed ML result ────────────────────────────────
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
            # Deep-copy so we don't mutate the cached MLResult.result dict
            response_data = {
                "status": "success",
                "computed_at": ml_result.computed_at,
                **copy.deepcopy(ml_result.result),
            }

        # ── Inject DB-computed averages into spend_optimization ────────
        # Always ensure spend_optimization exists if we have valid averages
        if avg_income > 0 or avg_expense > 0:
            if response_data.get("spend_optimization") is None:
                response_data["spend_optimization"] = {}

            response_data["spend_optimization"]["monthly_income_avg"] = avg_income
            response_data["spend_optimization"]["monthly_expense_avg"] = avg_expense

        return Response(
            RecommendationResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
