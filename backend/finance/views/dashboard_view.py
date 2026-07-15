import calendar
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from finance.models import Transaction, Goal
from serializers.dashboard_serializers import (
    DashboardQuerySerializer,
    DashboardTransactionSerializer,
    DashboardGoalSerializer
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _months_back(year, month, n):
    """Return list of (year, month) tuples for the last n months ending at year/month (inclusive, oldest first)."""
    result = []
    y, m = year, month
    for _ in range(n):
        result.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(result))


def _build_weekly_chart(transactions, year, month):
    """
    Aggregate transactions by week within a single month.
    Weeks: 1→days 1-7, 2→days 8-14, 3→days 15-21, 4→days 22-end.
    Returns {"labels": [...], "expense": [...], "savings": [...]}
    """
    income_w  = defaultdict(Decimal)
    expense_w = defaultdict(Decimal)

    for t in transactions:
        if t.date.year != year or t.date.month != month:
            continue
        day = t.date.day
        week = 1 if day <= 7 else (2 if day <= 14 else (3 if day <= 21 else 4))
        if t.transaction_type == "Income":
            income_w[week] += t.amount
        else:
            expense_w[week] += t.amount

    labels  = ["Week 1", "Week 2", "Week 3", "Week 4"]
    expense = [float(expense_w[w]) for w in range(1, 5)]
    savings = [float(income_w[w] - expense_w[w]) for w in range(1, 5)]
    return {"labels": labels, "expense": expense, "savings": savings}


def _build_monthly_chart(all_txns_by_month, month_list):
    """
    Aggregate pre-fetched transactions by month.
    month_list: list of (year, month) tuples, oldest first.
    Returns {"labels": [...], "expense": [...], "savings": [...]}
    """
    labels, expense_data, savings_data = [], [], []

    for y, m in month_list:
        txns     = all_txns_by_month.get((y, m), [])
        income   = sum(t.amount for t in txns if t.transaction_type == "Income")
        expense  = sum(t.amount for t in txns if t.transaction_type == "Expense")
        savings  = income - expense
        labels.append(f"{calendar.month_abbr[m]} {y}")
        expense_data.append(float(expense))
        savings_data.append(float(savings))

    return {"labels": labels, "expense": expense_data, "savings": savings_data}


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        # --- Validate query params ---
        query_serializer = DashboardQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(
                {"status": "error", "message": query_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Determine target month ---
        month_year = query_serializer.validated_data.get("month_year")
        if month_year:
            year, month = int(month_year[:4]), int(month_year[5:])
        else:
            today = timezone.now().date()
            year, month = today.year, today.month

        month_label = f"{year}-{month:02d}"

        # --- Determine previous month ---
        prev_month = month - 1 if month > 1 else 12
        prev_year  = year if month > 1 else year - 1

        # ----------------------------------------------------------------
        # Single wide query: fetch 6 months of transactions in one DB hit
        # ----------------------------------------------------------------
        six_month_list = _months_back(year, month, 6)
        oldest_year, oldest_month = six_month_list[0]

        # Build a date lower-bound (1st of the oldest month)
        import datetime
        date_from = datetime.date(oldest_year, oldest_month, 1)

        wide_txns = Transaction.objects.filter(
            user=request.user,
            date__gte=date_from,
            date__year__lte=year,
            date__month__lte=month if oldest_year == year else 12,
        ).order_by("-date")

        # Group fetched transactions by (year, month)
        txns_by_month = defaultdict(list)
        for t in wide_txns:
            txns_by_month[(t.date.year, t.date.month)].append(t)

        # Current-month and previous-month slices
        current_txns = txns_by_month.get((year, month), [])
        prev_txns    = txns_by_month.get((prev_year, prev_month), [])

        # ----------------------------------------------------------------
        # Summary cards — current month
        # ----------------------------------------------------------------
        total_income  = sum(t.amount for t in current_txns if t.transaction_type == "Income")
        total_expense = sum(t.amount for t in current_txns if t.transaction_type == "Expense")
        net_savings   = total_income - total_expense

        # Summary cards — previous month
        prev_income  = sum(t.amount for t in prev_txns if t.transaction_type == "Income")
        prev_expense = sum(t.amount for t in prev_txns if t.transaction_type == "Expense")
        prev_savings = prev_income - prev_expense

        def pct_change(current, previous):
            """% change, rounded to 2 dp. None when both are zero."""
            c, p = float(current), float(previous)
            if p == 0:
                return None if c == 0 else 100.0
            return round((c - p) / abs(p) * 100, 2)

        summary = {
            "total_income":       float(total_income),
            "total_expense":      float(total_expense),
            "net_savings":        float(net_savings),
            "income_change_pct":  pct_change(total_income,  prev_income),
            "expense_change_pct": pct_change(total_expense, prev_expense),
            "savings_change_pct": pct_change(net_savings,   prev_savings),
        }

        # ----------------------------------------------------------------
        # Chart data — 1M (weekly), 3M (monthly), 6M (monthly)
        # ----------------------------------------------------------------
        one_month_list   = [(year, month)]
        three_month_list = _months_back(year, month, 3)

        chart_data = {
            "1m": _build_weekly_chart(current_txns, year, month),
            "3m": _build_monthly_chart(txns_by_month, three_month_list),
            "6m": _build_monthly_chart(txns_by_month, six_month_list),
        }

        # ----------------------------------------------------------------
        # Spending breakdown by category — current month
        # ----------------------------------------------------------------
        category_totals = defaultdict(Decimal)
        for t in current_txns:
            if t.transaction_type == "Expense":
                category_totals[t.category] += t.amount

        spending_breakdown = sorted(
            [{"category": cat, "amount": float(amt)} for cat, amt in category_totals.items()],
            key=lambda x: x["amount"],
            reverse=True,
        )

        # ----------------------------------------------------------------
        # Fetch active goals
        # ----------------------------------------------------------------
        goals = Goal.objects.filter(user=request.user, status="current")

        has_transactions = Transaction.objects.filter(user=request.user).exists()

        # ----------------------------------------------------------------
        # Build response
        # ----------------------------------------------------------------
        response_data = {
            "status":       "success",
            "message":      f"Dashboard data for {month_label}",
            "month":        month_label,
            "user": {
                "id":       request.user.id,
                "username": request.user.username,
                "email":    request.user.email,
            },
            "summary":            summary,
            "chart_data":         chart_data,
            "spending_breakdown": spending_breakdown,
            "transactions": DashboardTransactionSerializer(current_txns, many=True).data,
            "goals":        DashboardGoalSerializer(goals, many=True).data,
            "has_transactions":   has_transactions,
        }

        return Response(response_data, status=status.HTTP_200_OK)
