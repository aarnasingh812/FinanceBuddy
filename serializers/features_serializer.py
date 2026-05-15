from rest_framework import serializers
from finance.models import RecurringTransaction

class RecurringTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringTransaction
        fields = (
            'id', 'title', 'amount', 'interval_bucket', 'mean_gap_days',
            'confidence', 'next_expected_date', 'recurring_type',
            'occurrences', 'last_date', 'is_active',
        )