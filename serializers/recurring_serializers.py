from rest_framework import serializers


# ---------------------------------------------------------------------------
# GET /recurring — Response
# ---------------------------------------------------------------------------

class RecurringPatternSerializer(serializers.Serializer):
    """
    Serializes a single recurring pattern dict produced by the ML engine.
    These are raw dicts stored in the MLResult JSONField, not model instances.
    """
    title = serializers.CharField(read_only=True)
    amount = serializers.FloatField(read_only=True)
    mean_gap_days = serializers.FloatField(read_only=True)
    confidence = serializers.FloatField(read_only=True)
    next_expected_date = serializers.CharField(read_only=True, allow_null=True)
    recurring_type = serializers.CharField(read_only=True)
    occurrences = serializers.IntegerField(read_only=True)
    last_date = serializers.CharField(read_only=True)
    transaction_ids = serializers.ListField(
        child=serializers.IntegerField(), read_only=True, required=False
    )


class RecurringBucketSerializer(serializers.Serializer):
    """
    Serializes the three interval buckets for recurring transactions.
    Each bucket is either a list of patterns or null.
    """
    field_15_days = RecurringPatternSerializer(
        many=True, read_only=True, allow_null=True, source='15_days', required=False
    )
    field_30_days = RecurringPatternSerializer(
        many=True, read_only=True, allow_null=True, source='30_days', required=False
    )
    field_90_days = RecurringPatternSerializer(
        many=True, read_only=True, allow_null=True, source='90_days', required=False
    )

    def to_representation(self, instance):
        """Keep the original underscore-dotted keys in the output."""
        ret = {}
        for bucket in ('15_days', '30_days', '90_days'):
            val = instance.get(bucket) if isinstance(instance, dict) else None
            if val is not None:
                ret[bucket] = RecurringPatternSerializer(val, many=True).data
            else:
                ret[bucket] = None
        return ret


class RecurringTransactionResponseSerializer(serializers.Serializer):
    """Serializes the full response for GET /recurring."""
    status = serializers.CharField(read_only=True)
    computed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    message = serializers.CharField(read_only=True, required=False)
    recurring_transactions = serializers.SerializerMethodField()

    def get_recurring_transactions(self, obj):
        data = obj.get('recurring_transactions')
        if data is None:
            return None
        return RecurringBucketSerializer(data).data


# ---------------------------------------------------------------------------
# PUT /recurring — Request & Response
# ---------------------------------------------------------------------------

class RecurringUpdateSerializer(serializers.Serializer):
    """Validates the request body for PUT /recurring."""
    id = serializers.IntegerField(
        help_text="Primary key of the RecurringTransaction to update."
    )
    is_active = serializers.BooleanField(
        help_text="Set to true to activate or false to dismiss the recurring transaction."
    )


class RecurringUpdateResponseSerializer(serializers.Serializer):
    """Serializes the success response for PUT /recurring."""
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
