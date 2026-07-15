
import logging
import time

from celery import shared_task
from concurrent.futures import ThreadPoolExecutor
from datetime import date as date_type

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, name="finance.run_ml_compute")
def run_ml_compute(self, user_id: int) -> dict:
    
    # Import inside task to avoid circular imports and ensure the Django ORM
    # is fully initialised when the worker process calls this function.
    from finance.models import MLResult, RecurringTransaction, AnomalousTransaction
    from finance.models.base_models import User
    #from ml_utils.recurring_detector import detect_recurring_transactions
    from ml_utils.anomaly_detector import detect_anomalies
    from ml_utils.goal_forecaster import forecast_goals
    from ml_utils.recommendation_engine import generate_recommendations

    task_start = time.time()
    logger.info(
        "[ML Compute] Task started | task_id=%s user_id=%s",
        self.request.id, user_id,
    )

    user = User.objects.get(pk=user_id)
    results_stored = {}



    # ------------------------------------------------------------------
    # 2. Run independent ML engines in parallel
    #    (recurring, anomaly, forecast have no inter-dependencies)
    # ------------------------------------------------------------------
    logger.info(
        "[ML Compute] Dispatching parallel engines: recurring, anomaly, forecast | user_id=%s",
        user_id,
    )
    parallel_start = time.time()

    with ThreadPoolExecutor(max_workers=3) as pool:
       # recurring_future = pool.submit(detect_recurring_transactions, user.id)
        anomaly_future = pool.submit(detect_anomalies, user.id)
        forecast_future = pool.submit(forecast_goals, user.id)

    # recurring_raw = recurring_future.result()
    # logger.info(
    #     "[ML Compute] Engine complete: recurring | user_id=%s elapsed=%.2fs",
    #     user_id, time.time() - parallel_start,
    # )

    anomaly_raw = anomaly_future.result()
    logger.info(
        "[ML Compute] Engine complete: anomaly | user_id=%s elapsed=%.2fs",
        user_id, time.time() - parallel_start,
    )

    forecast_raw = forecast_future.result()
    logger.info(
        "[ML Compute] Engine complete: forecast | user_id=%s elapsed=%.2fs",
        user_id, time.time() - parallel_start,
    )

    logger.info(
        "[ML Compute] All parallel engines finished | user_id=%s total_parallel=%.2fs",
        user_id, time.time() - parallel_start,
    )

    # ------------------------------------------------------------------
    # 3. Persist recurring transaction results
    # ------------------------------------------------------------------
    # logger.info("[ML Compute] Persisting recurring results | user_id=%s", user_id)
    # upserted_ids = []
    # for bucket_key, patterns in recurring_raw.items():
    #     if patterns is None:
    #         continue
    #     for pattern in patterns:
    #         obj, _ = RecurringTransaction.objects.update_or_create(
    #             user=user,
    #             title=pattern["title"],
    #             amount=pattern["amount"],
    #             interval_bucket=bucket_key,
    #             defaults={
    #                 "mean_gap_days": pattern["mean_gap_days"],
    #                 "confidence": pattern["confidence"],
    #                 "next_expected_date": date_type.fromisoformat(pattern["next_expected_date"]),
    #                 "recurring_type": pattern["recurring_type"],
    #                 "occurrences": pattern["occurrences"],
    #                 "last_date": date_type.fromisoformat(pattern["last_date"]),
    #                 "is_active": True,
    #             },
    #         )
    #         upserted_ids.append(obj.id)
    # RecurringTransaction.objects.filter(user=user).exclude(id__in=upserted_ids).update(is_active=False)

    # MLResult.objects.create(
    #     user=user,
    #     feature="recurring",
    #     result={"recurring_transactions": recurring_raw},
    # )
    # results_stored["recurring"] = True
    # logger.info(
    #     "[ML Compute] Persisted recurring | user_id=%s upserted=%d",
    #     user_id, len(upserted_ids),
    # )

    # ------------------------------------------------------------------
    # 4. Persist anomaly detection results
    # ------------------------------------------------------------------
    logger.info("[ML Compute] Persisting anomaly results | user_id=%s", user_id)
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
        logger.info(
            "[ML Compute] Persisted anomalies | user_id=%s upserted=%d",
            user_id, len(upserted_ids),
        )
    else:
        logger.info(
            "[ML Compute] Skipped anomaly persistence (insufficient data) | user_id=%s",
            user_id,
        )

    MLResult.objects.create(
        user=user,
        feature="anomaly",
        result={"anomalies": anomaly_raw},
    )
    results_stored["anomaly"] = True

    # ------------------------------------------------------------------
    # 5. Persist goal forecast results
    # ------------------------------------------------------------------
    logger.info("[ML Compute] Persisting forecast results | user_id=%s", user_id)
    MLResult.objects.create(
        user=user,
        feature="forecast",
        result=forecast_raw if forecast_raw else {
            "savings_summary": None,
            "allocation_plan": None,
            "forecasts": None,
        },
    )
    results_stored["forecast"] = True
    logger.info(
        "[ML Compute] Persisted forecast | user_id=%s has_data=%s",
        user_id, bool(forecast_raw),
    )

    # ------------------------------------------------------------------
    # 6. Recommendations & Insights (depends on steps 2-5)
    # ------------------------------------------------------------------
    logger.info("[ML Compute] Computing recommendations | user_id=%s", user_id)
    rec_start = time.time()
    recommendation_raw = generate_recommendations(
        user.id,
        # recurring_data=recurring_raw,
        anomaly_data=anomaly_raw,
        forecast_data=forecast_raw,
    )
    logger.info(
        "[ML Compute] Recommendations complete | user_id=%s elapsed=%.2fs",
        user_id, time.time() - rec_start,
    )

    MLResult.objects.create(
        user=user,
        feature="recommendation",
        result=recommendation_raw if recommendation_raw else {
            "savings_opportunities": None,
            "spend_optimization": None,
            "goal_insights": None,
        },
    )
    results_stored["recommendation"] = True

    logger.info(
        "[ML Compute] Task complete | task_id=%s user_id=%s total_elapsed=%.2fs features=%s",
        self.request.id, user_id, time.time() - task_start, list(results_stored.keys()),
    )
    return results_stored
