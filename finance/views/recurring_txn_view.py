
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from serializers.features_serializer import RecurringTransactionSerializer
from ml_utils.recurring_detector import detect_recurring_transactions
from finance.models import RecurringTransaction
from datetime import date as date_type


class RecurringTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Run detection engine
        detected = detect_recurring_transactions(user.id)

        # Upsert results into RecurringTransaction model
        # First, gather all keys we're about to upsert so we can deactivate stale ones
        upserted_ids = []

        for bucket_key, patterns in detected.items():
            if patterns is None:
                continue
            for pattern in patterns:
                obj, _created = RecurringTransaction.objects.update_or_create(
                    user=user,
                    title=pattern["title"],
                    amount=pattern["amount"],
                    interval_bucket=bucket_key,
                    defaults={
                        "mean_gap_days": pattern["mean_gap_days"],
                        "confidence": pattern["confidence"],
                        "next_expected_date": date_type.fromisoformat(pattern["next_expected_date"]),
                        "recurring_type": pattern["recurring_type"],
                        "occurrences": pattern["occurrences"],
                        "last_date": date_type.fromisoformat(pattern["last_date"]),
                        "is_active": True,
                    },
                )
                upserted_ids.append(obj.id)

        # Mark patterns that were not detected anymore as inactive
        RecurringTransaction.objects.filter(
            user=user
        ).exclude(
            id__in=upserted_ids
        ).update(is_active=False)

        # Build the response from persisted data (respects user dismissals)
        all_recurring = RecurringTransaction.objects.filter(user=user, is_active=True)

        bucket_response = {}
        for bucket_key in ["15_days", "30_days", "90_days"]:
            bucket_qs = all_recurring.filter(interval_bucket=bucket_key)
            if bucket_qs.exists():
                serializer = RecurringTransactionSerializer(bucket_qs, many=True)
                bucket_response[bucket_key] = serializer.data
            else:
                bucket_response[bucket_key] = None

        return Response({
            "status": "success",
            "recurring_transactions": bucket_response
        }, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        recurring_id = request.data.get("id")
        is_active = request.data.get("is_active")

        if recurring_id is None or is_active is None:
            return Response(
                {"error": "Both 'id' and 'is_active' fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            recurring = RecurringTransaction.objects.get(id=recurring_id, user=request.user)
        except RecurringTransaction.DoesNotExist:
            return Response(
                {"error": "Recurring transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        recurring.is_active = bool(is_active)
        recurring.save()

        return Response({
            "status": "success",
            "message": f"Recurring transaction {'activated' if recurring.is_active else 'dismissed'} successfully.",
        }, status=status.HTTP_200_OK)
