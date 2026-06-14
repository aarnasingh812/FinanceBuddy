from rest_framework import serializers


class MLComputeFeaturesSerializer(serializers.Serializer):
    """Serializes the features_computed dict in the ML compute response."""
    recurring = serializers.BooleanField(read_only=True)
    anomaly = serializers.BooleanField(read_only=True)
    forecast = serializers.BooleanField(read_only=True)
    recommendation = serializers.BooleanField(read_only=True)


class MLComputeResponseSerializer(serializers.Serializer):
    """Serializes the success response for POST /ml/compute (legacy synchronous)."""
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    features_computed = MLComputeFeaturesSerializer(read_only=True)


class MLComputeAcceptedSerializer(serializers.Serializer):
    """Serializes the 202 Accepted response when a task is dispatched."""
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    task_id = serializers.CharField(read_only=True)


class MLComputeStatusSerializer(serializers.Serializer):
    """Serializes the GET /ml/compute/status/<task_id> response."""
    task_id = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    result = serializers.DictField(required=False, allow_null=True, read_only=True)
    error = serializers.CharField(required=False, allow_null=True, read_only=True)
