from rest_framework import serializers
from finance.models import RecurringTransaction, AnomalousTransaction

class RecurringTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringTransaction
        fields = (
            'id', 'title', 'amount', 'interval_bucket', 'mean_gap_days',
            'confidence', 'next_expected_date', 'recurring_type',
            'occurrences', 'last_date', 'is_active',
        )


class AnomalousTransactionSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='transaction.title', read_only=True)
    amount = serializers.DecimalField(
        source='transaction.amount', max_digits=10, decimal_places=2, read_only=True
    )
    date = serializers.DateField(source='transaction.date', read_only=True)
    category = serializers.CharField(source='transaction.category', read_only=True)
    transaction_id = serializers.IntegerField(source='transaction.id', read_only=True)

    class Meta:
        model = AnomalousTransaction
        fields = (
            'id', 'transaction_id', 'title', 'amount', 'date', 'category',
            'anomaly_score', 'signals', 'period', 'is_dismissed', 'detected_at',
        )


class GoalForecastSerializer(serializers.Serializer):
    goal_id = serializers.IntegerField()
    goal_name = serializers.CharField()
    target_amount = serializers.FloatField()
    deadline = serializers.CharField()
    current_savings = serializers.FloatField()
    remaining_amount = serializers.FloatField()
    progress_percent = serializers.FloatField()
    months_remaining = serializers.IntegerField()
    allocated_monthly_savings = serializers.FloatField()
    required_monthly_savings = serializers.FloatField()
    predicted_achievement_date = serializers.CharField(allow_null=True)
    on_track = serializers.BooleanField()
    confidence = serializers.FloatField()
    status = serializers.CharField()