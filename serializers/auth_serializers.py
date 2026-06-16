from rest_framework import serializers


class LogoutRequestSerializer(serializers.Serializer):
    """Validates the request body for POST /logout."""
    refresh_token = serializers.CharField(
        help_text="The JWT refresh token to blacklist."
    )


class LogoutResponseSerializer(serializers.Serializer):
    """Serializes the success response for POST /logout."""
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
