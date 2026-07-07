from rest_framework import serializers


# ---------------------------------------------------------------------------
# Projection — nested inside each forecast item
# ---------------------------------------------------------------------------

class GoalProjectionSerializer(serializers.Serializer):
    """Serializes a single scenario projection (optimistic/realistic/pessimistic)."""
    scenario = serializers.CharField(read_only=True)
    monthly_savings_rate = serializers.FloatField(read_only=True)
    months_to_goal = serializers.IntegerField(read_only=True, allow_null=True)
    estimated_completion_date = serializers.CharField(read_only=True, allow_null=True)


# ---------------------------------------------------------------------------
# Individual Forecast Item
# ---------------------------------------------------------------------------

class GoalForecastItemSerializer(serializers.Serializer):
    """Serializes per-goal forecast data including three-scenario projections."""
    goal_id = serializers.IntegerField(read_only=True)
    goal_name = serializers.CharField(read_only=True)
    target_amount = serializers.FloatField(read_only=True)
    deadline = serializers.CharField(read_only=True)
    current_savings = serializers.FloatField(read_only=True)
    remaining_amount = serializers.FloatField(read_only=True)
    progress_percent = serializers.FloatField(read_only=True)
    months_remaining = serializers.IntegerField(read_only=True)
    allocated_monthly_savings = serializers.FloatField(read_only=True)
    required_monthly_savings = serializers.FloatField(read_only=True)
    predicted_achievement_date = serializers.CharField(read_only=True, allow_null=True)
    on_track = serializers.BooleanField(read_only=True)
    confidence = serializers.FloatField(read_only=True)
    status = serializers.CharField(read_only=True)
    projections = GoalProjectionSerializer(many=True, read_only=True, allow_null=True)


# ---------------------------------------------------------------------------
# Savings Summary & Allocation Plan
# ---------------------------------------------------------------------------

class SavingsSummarySerializer(serializers.Serializer):
    """Serializes the savings summary section of the forecast response."""
    avg_monthly_savings = serializers.FloatField(read_only=True)
    savings_trend = serializers.CharField(read_only=True)
    total_savings = serializers.FloatField(read_only=True)


class AllocationPlanSerializer(serializers.Serializer):
    """Serializes the allocation plan section of the forecast response."""
    total_goals = serializers.IntegerField(read_only=True)
    achievable_goals = serializers.IntegerField(read_only=True)
    budget_utilization_percent = serializers.FloatField(read_only=True)


# ---------------------------------------------------------------------------
# Full Response
# ---------------------------------------------------------------------------

class GoalForecastResponseSerializer(serializers.Serializer):
    """Serializes the full response for GET /goal/forecast."""
    status = serializers.CharField(read_only=True)
    computed_at = serializers.DateTimeField(read_only=True, allow_null=True, required=False)
    message = serializers.CharField(read_only=True, required=False)
    savings_summary = SavingsSummarySerializer(read_only=True, allow_null=True)
    allocation_plan = AllocationPlanSerializer(read_only=True, allow_null=True)
    forecasts = GoalForecastItemSerializer(many=True, read_only=True, allow_null=True)
