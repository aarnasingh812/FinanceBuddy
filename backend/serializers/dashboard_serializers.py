from rest_framework import serializers


# ---------------------------------------------------------------------------
# Dashboard — Query Params
# ---------------------------------------------------------------------------

class DashboardQuerySerializer(serializers.Serializer):
    """Validates the optional month_year query parameter for GET /dashboard."""
    month_year = serializers.RegexField(
        regex=r'^\d{4}-\d{2}$',
        required=False,
        help_text="Filter by month in YYYY-MM format (e.g. 2026-06). Defaults to current month."
    )


# ---------------------------------------------------------------------------
# Dashboard — Response
# ---------------------------------------------------------------------------

class DashboardTransactionSerializer(serializers.Serializer):
    """Serializes a single transaction for the dashboard."""
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    transaction_type = serializers.CharField(read_only=True)
    date = serializers.DateField(read_only=True)
    category = serializers.CharField(read_only=True)


class DashboardGoalSerializer(serializers.Serializer):
    """Serializes a single goal for the dashboard."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    target_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    deadline = serializers.DateField(read_only=True)
    status = serializers.CharField(read_only=True)


class DashboardUserSerializer(serializers.Serializer):
    """Serializes user info for the dashboard."""
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class DashboardResponseSerializer(serializers.Serializer):
    """Serializes the full response for GET /dashboard."""
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    month = serializers.CharField(read_only=True, help_text="The YYYY-MM month being displayed.")
    user = DashboardUserSerializer(read_only=True)
    transactions = DashboardTransactionSerializer(many=True, read_only=True)
    goals = DashboardGoalSerializer(many=True, read_only=True)
    summary = serializers.DictField(
        read_only=True,
        help_text=(
            "total_income, total_expense, net_savings, "
            "income_change_pct, expense_change_pct, savings_change_pct "
            "(% change vs previous month; null when both months have no data)."
        ),
    )
    chart_data = serializers.DictField(
        read_only=True,
        help_text=(
            "Time-series data for line graphs. Keys: '1m' (weekly, current month), "
            "'3m' (monthly, last 3 months), '6m' (monthly, last 6 months). "
            "Each value: {labels: [...], expense: [...], savings: [...]}."
        ),
    )

