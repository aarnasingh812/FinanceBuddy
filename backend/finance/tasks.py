"""
Celery tasks for heavy ML computation.

All logic previously in MLComputeView.post() has been moved here so that
it executes in the Celery worker process — outside the HTTP request cycle.
"""

from celery import shared_task
from datetime import date as date_type


@shared_task(bind=True, name="finance.run_ml_compute")
def run_ml_compute(self, user_id: int) -> dict:
    
    # Import inside task to avoid circular imports and ensure the Django ORM
    # is fully initialised when the worker process calls this function.
    from finance.models import MLResult, RecurringTransaction, AnomalousTransaction
    from finance.models.base_models import User
    from ml_utils.recurring_detector import detect_recurring_transactions
    from ml_utils.anomaly_detector import detect_anomalies
    from ml_utils.goal_forecaster import forecast_goals
    from ml_utils.recommendation_engine import generate_recommendations

    user = User.objects.get(pk=user_id)
    results_stored = {}

    # ------------------------------------------------------------------
    # 1. Soft-delete all existing current results for this user
    # ------------------------------------------------------------------
    MLResult.objects.filter(user=user, status=True).update(status=False)

    # ------------------------------------------------------------------
    # 2. Recurring Transaction Detection
    # ------------------------------------------------------------------
    recurring_raw = detect_recurring_transactions(user.id)

    upserted_ids = []
    for bucket_key, patterns in recurring_raw.items():
        if patterns is None:
            continue
        for pattern in patterns:
            obj, _ = RecurringTransaction.objects.update_or_create(
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
    RecurringTransaction.objects.filter(user=user).exclude(id__in=upserted_ids).update(is_active=False)

    MLResult.objects.create(
        user=user,
        feature="recurring",
        result={"recurring_transactions": recurring_raw},
        status=True,
    )
    results_stored["recurring"] = True

    # ------------------------------------------------------------------
    # 3. Anomaly Detection
    # ------------------------------------------------------------------
    anomaly_raw = detect_anomalies(user.id)

    if not anomaly_raw.get("insufficient_data"):
        upserted_ids = []
        for period_key in ("current_month", "last_3_months"):
            anomalies = anomaly_raw.get(period_key)
            if anomalies is None:
                continue
            for anomaly in anomalies:
                obj, _ = AnomalousTransaction.objects.update_or_create(
                    user=user,
                    transaction_id=anomaly["transaction_id"],
                    period=period_key,
                    defaults={
                        "anomaly_score": anomaly["anomaly_score"],
                        "signals": anomaly["anomaly_reasons"],
                    },
                )
                upserted_ids.append(obj.id)
        AnomalousTransaction.objects.filter(user=user).exclude(id__in=upserted_ids).update(is_dismissed=True)

    MLResult.objects.create(
        user=user,
        feature="anomaly",
        result={"anomalies": anomaly_raw},
        status=True,
    )
    results_stored["anomaly"] = True

    # ------------------------------------------------------------------
    # 4. Goal Forecast
    # ------------------------------------------------------------------
    forecast_raw = forecast_goals(user.id)

    MLResult.objects.create(
        user=user,
        feature="forecast",
        result=forecast_raw if forecast_raw else {
            "savings_summary": None,
            "allocation_plan": None,
            "forecasts": None,
        },
        status=True,
    )
    results_stored["forecast"] = True

    # ------------------------------------------------------------------
    # 5. Recommendations & Insights
    # ------------------------------------------------------------------
    recommendation_raw = generate_recommendations(user.id)

    MLResult.objects.create(
        user=user,
        feature="recommendation",
        result=recommendation_raw if recommendation_raw else {
            "savings_opportunities": None,
            "spend_optimization": None,
            "goal_insights": None,
        },
        status=True,
    )
    results_stored["recommendation"] = True

    return results_stored
