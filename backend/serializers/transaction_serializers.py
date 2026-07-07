from rest_framework import serializers


# ---------------------------------------------------------------------------
# Transaction List
# ---------------------------------------------------------------------------

class TransactionListQuerySerializer(serializers.Serializer):
    """Validates query params for GET /transaction/list."""
    month = serializers.RegexField(
        regex=r'^\d{4}-\d{2}$',
        required=False,
        help_text="Filter by month in YYYY-MM format (e.g. 2026-06)."
    )


class TransactionItemSerializer(serializers.Serializer):
    """Serializes a single transaction for list responses."""
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    transaction_type = serializers.CharField(read_only=True)
    date = serializers.DateField(read_only=True)
    category = serializers.CharField(read_only=True)



class TransactionListResponseSerializer(serializers.Serializer):
    """Serializes the response for GET /transaction/list."""
    status = serializers.CharField(read_only=True)
    transactions = TransactionItemSerializer(many=True, read_only=True)


# ---------------------------------------------------------------------------
# Bulk Transaction
# ---------------------------------------------------------------------------

class BulkTransactionQuerySerializer(serializers.Serializer):
    """Validates query params for GET & POST /transaction/bulk."""
    mode = serializers.ChoiceField(
        choices=['download', 'upload'],
        help_text="Use 'download' to get the template or 'upload' to import transactions."
    )


class CreatedTransactionSerializer(serializers.Serializer):
    """Serializes a single successfully created transaction in a bulk upload."""
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    amount = serializers.CharField(read_only=True)
    transaction_type = serializers.CharField(read_only=True)
    date = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)


class BulkTransactionSuccessResponseSerializer(serializers.Serializer):
    """Serializes the success response for POST /transaction/bulk."""
    status = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    transactions = CreatedTransactionSerializer(many=True, read_only=True)


class BulkTransactionErrorResponseSerializer(serializers.Serializer):
    """Serializes the error response for POST /transaction/bulk."""
    status = serializers.CharField(read_only=True)
    error = serializers.CharField(read_only=True)
    row_errors = serializers.DictField(
        child=serializers.DictField(), required=False, read_only=True
    )
    total_rows = serializers.IntegerField(required=False, read_only=True)
    failed_rows = serializers.IntegerField(required=False, read_only=True)
