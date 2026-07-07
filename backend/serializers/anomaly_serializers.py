from rest_framework import serializers


# ---------------------------------------------------------------------------
# GET /anomalies — Response
# ---------------------------------------------------------------------------

class AnomalySignalSerializer(serializers.Serializer):
    """Serializes a single anomaly signal/reason within an anomalous transaction."""
    signal = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)
    score = serializers.FloatField(read_only=True)


class AnomalyItemSerializer(serializers.Serializer):
    """Serializes a single anomalous transaction from the ML engine output."""
    transaction_id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    amount = serializers.FloatField(read_only=True)
    date = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    anomaly_score = serializers.FloatField(read_only=True)
    anomaly_reasons = AnomalySignalSerializer(many=True, read_only=True)
    ml_contributed = serializers.BooleanField(read_only=True, required=False)


class AnomalyWindowSerializer(serializers.Serializer):
    """
    Serializes all anomaly windows.
    Each window key maps to a list of anomaly items or null.
    """
    current_month = AnomalyItemSerializer(many=True, read_only=True, allow_null=True)
    last_3_months = AnomalyItemSerializer(many=True, read_only=True, allow_null=True)
    current_month_income_anomalies = AnomalyItemSerializer(
        many=True, read_only=True, allow_null=True, required=False
    )
    last_3_months_income_anomalies = AnomalyItemSerializer(
        many=True, read_only=True, allow_null=True, required=False
    )
    ml_active = serializers.BooleanField(read_only=True, required=False)
    ml_min_samples_required = serializers.IntegerField(read_only=True, required=False)
    user_total_expenses = serializers.IntegerField(read_only=True, required=False)
    insufficient_data = serializers.BooleanField(read_only=True, required=False)


class AnomalyResponseSerializer(serializers.Serializer):
    """Serializes the full response for GET /anomalies."""
    status = serializers.CharField(read_only=True)
    computed_at = serializers.DateTimeField(read_only=True, allow_null=True, required=False)
    message = serializers.CharField(read_only=True, required=False)
    anomalies = AnomalyWindowSerializer(read_only=True, allow_null=True)


# ---------------------------------------------------------------------------
# PUT /anomalies — Request & Response
# ---------------------------------------------------------------------------

class AnomalyUpdateSerializer(serializers.Serializer):
    """Validates the request body for PUT /anomalies."""
    id = serializers.IntegerField(
        help_text="Primary key of the AnomalousTransaction record to update."
    )
    is_dismissed = serializers.BooleanField(
        help_text="Set to true to dismiss the anomaly, false to restore it."
    )


class AnomalyUpdateResponseSerializer(serializers.Serializer):
    """Serializes the success response for PUT /anomalies."""
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
