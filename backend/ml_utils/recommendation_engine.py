import logging
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from finance.models import Transaction, Goal, User
#from ml_utils.recurring_detector import detect_recurring_transactions
from ml_utils.anomaly_detector import detect_anomalies
from ml_utils.goal_forecaster import forecast_goals
from ml_utils.llm_client import generate_narrative

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DISCRETIONARY_CATEGORIES = [
    "entertainment", "shopping", "dining", "food", "travel",
    "clothing", "gifts", "subscriptions", "hobbies", "personal",
    "restaurants", "movies", "games", "sports", "beauty",
]

CUT_PERCENT = 10          # suggest cutting discretionary by 10 %
MIN_CATEGORY_SPEND = 500  # ignore categories below this monthly avg

RECURRING_BUCKET_KEYS = ("15_days", "30_days", "90_days")
ANOMALY_PERIOD_KEYS = ("current_month", "last_3_months")
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Helpers — Spending Analysis
# ---------------------------------------------------------------------------

def _category_trend(monthly_map, sorted_months):
    """Compare the most recent month to the average of prior months."""
    if len(sorted_months) < 3:
        return "stable"

    recent = monthly_map[sorted_months[-1]]
    prior_avg = mean(monthly_map[k] for k in sorted_months[:-1])
    if prior_avg <= 0:
        return "stable"

    change = (recent - prior_avg) / prior_avg
    if change > 0.15:
        return "rising"
    if change < -0.15:
        return "falling"
    return "stable"


def _compute_category_monthly_spend(user_id, txns=None):
    """
    Aggregate transactions by category and month.

    Parameters
    ----------
    user_id : int
    txns : list[dict] | None
        Pre-fetched transaction rows (avoids an extra DB call when the
        caller already has them).  Each dict must have keys:
        ``amount``, ``date``, ``transaction_type``, ``category``.
        When *None*, the rows are fetched from the DB directly (fallback
        for standalone / test usage).
    """
    today = date.today()
    last_month_end = date(today.year, today.month, 1) - timedelta(days=1)
    current_ym = (last_month_end.year, last_month_end.month)

    if txns is None:
        # Standalone fallback: single bounded query, no .exists() pre-check.
        start_date = date(today.year - 1, today.month, 1)
        txns = list(
            Transaction.objects
            .filter(user_id=user_id, date__gte=start_date, date__lte=last_month_end)
            .order_by("date")
            .values("amount", "date", "transaction_type", "category")
        )

    if not txns:
        return {}, {}

    # Aggregate per category per month (expenses only)
    cat_monthly = defaultdict(lambda: defaultdict(float))
    income_monthly = defaultdict(float)
    expense_monthly = defaultdict(float)

    for t in txns:
        ym = (t["date"].year, t["date"].month)
        amt = float(t["amount"])
        if t["transaction_type"] == "Expense":
            cat_monthly[t["category"]][ym] += amt
            expense_monthly[ym] += amt
        else:
            income_monthly[ym] += amt

    # Build stats per category
    cat_stats = {}
    for cat, monthly_map in cat_monthly.items():
        totals = list(monthly_map.values())
        sorted_months = sorted(monthly_map.keys())

        cat_stats[cat] = {
            "monthly_totals": dict(monthly_map),
            "avg_monthly": round(mean(totals) if totals else 0.0, 2),
            "current_month": round(monthly_map.get(current_ym, 0.0), 2),
            "trend": _category_trend(monthly_map, sorted_months),
            "total": round(sum(totals), 2),
        }

    total_months = len(expense_monthly) or 1
    overall = {
        "avg_monthly_expense": round(sum(expense_monthly.values()) / total_months, 2),
        "current_month_expense": round(expense_monthly.get(current_ym, 0.0), 2),
        "avg_monthly_income": round(sum(income_monthly.values()) / total_months, 2),
        "total_months": total_months,
    }

    return cat_stats, overall


def _is_discretionary(category):
    """Check if a category is likely discretionary."""
    return category.strip().lower() in DISCRETIONARY_CATEGORIES


def _sort_by_savings_desc(recs):
    recs.sort(key=lambda r: r["estimated_monthly_savings"], reverse=True)
    return recs


# ---------------------------------------------------------------------------
# Recommendation generators (each returns a list of rec dicts)
# ---------------------------------------------------------------------------

def _subscription_recommendations(recurring_data):
    """Suggest cancelling low-priority recurring subscriptions."""
    recs = []
    if not recurring_data:
        return recs

    for bucket_key in RECURRING_BUCKET_KEYS:
        for p in recurring_data.get(bucket_key) or []:
            rtype = p.get("recurring_type", "")
            if rtype not in ("Subscription", "Bill"):
                continue

            amt = float(p["amount"])
            gap = p.get("mean_gap_days", 30)
            monthly_cost = round(amt * (30 / max(gap, 1)), 2)  # normalise to monthly

            recs.append({
                "type": "subscription_review",
                "title": f"Review '{p['title']}' subscription",
                "detail": (
                    f"You're paying {amt:.2f} every ~{gap:.0f} days for "
                    f"'{p['title']}'. That's approximately {monthly_cost:.2f}/month. "
                    f"If you no longer need it, cancelling could save you "
                    f"{monthly_cost:.2f} per month."
                ),
                "estimated_monthly_savings": monthly_cost,
                "priority": "high" if monthly_cost >= 500 else "medium",
            })

    return _sort_by_savings_desc(recs)


def _anomaly_based_recommendations(anomaly_data, cat_stats):
    """Suggest reducing spend in categories with anomalous transactions."""
    recs = []
    if not anomaly_data:
        return recs

    # Collect categories that triggered anomalies
    flagged_categories = set()
    for period in ANOMALY_PERIOD_KEYS:
        for a in anomaly_data.get(period) or []:
            cat = a.get("category", "")
            if cat:
                flagged_categories.add(cat)

    for cat in flagged_categories:
        stats = cat_stats.get(cat, {})
        avg = stats.get("avg_monthly", 0)
        current = stats.get("current_month", 0)

        if avg < MIN_CATEGORY_SPEND:
            continue

        # Compare this month's spend against the monthly average
        excess = round(current - avg, 2) if current > avg else 0
        if excess > 0:
            recs.append({
                "type": "anomaly_reduction",
                "title": f"Unusual spending in '{cat}'",
                "detail": (
                    f"You are spending more on '{cat}' — last month you spent "
                    f"{current:.2f}, which is {excess:.2f} above your monthly "
                    f"average of {avg:.2f}. Try to reduce your '{cat}' spending "
                    f"closer to average this month to save ~{excess:.2f}."
                ),
                "estimated_monthly_savings": excess,
                "priority": "high" if excess >= 1000 else "medium",
            })

    return recs


def _discretionary_cut_recommendations(cat_stats):
    """Suggest a percentage cut in top discretionary categories based on
    current month spend vs monthly average."""
    discretionary_cats = [
        (cat, stats) for cat, stats in cat_stats.items()
        if _is_discretionary(cat) and stats["avg_monthly"] >= MIN_CATEGORY_SPEND
    ]
    # Sort by current month spend so the most active categories surface first
    discretionary_cats.sort(key=lambda x: -x[1]["current_month"])

    recs = []
    for cat, stats in discretionary_cats[:3]:
        avg = stats["avg_monthly"]
        current = stats["current_month"]

        # Only recommend a cut when spending this month exceeds the average
        if current <= avg:
            continue

        saving = round(current * CUT_PERCENT / 100, 2)
        excess = round(current - avg, 2)
        recs.append({
            "type": "discretionary_cut",
            "title": f"Reduce '{cat}' spending by {CUT_PERCENT}%",
            "detail": (
                f"You are spending more on '{cat}' — last month you spent "
                f"{current:.2f}, which is {excess:.2f} above your monthly "
                f"average of {avg:.2f}. Try to reduce it by {CUT_PERCENT}% "
                f"this month to save {saving:.2f}."
            ),
            "estimated_monthly_savings": saving,
            "priority": "medium",
        })

    return recs


def _trend_based_recommendations(cat_stats, overall):
    """Flag categories with rising spend trends."""
    recs = []
    for cat, stats in cat_stats.items():
        if stats["trend"] != "rising" or stats["avg_monthly"] < MIN_CATEGORY_SPEND:
            continue

        cur = stats["current_month"]
        avg = stats["avg_monthly"]
        excess = round(cur - avg, 2)
        if excess > 0:
            recs.append({
                "type": "rising_trend",
                "title": f"'{cat}' spending is rising",
                "detail": (
                    f"You are spending more on '{cat}' — last month you spent "
                    f"{cur:.2f} vs your average of {avg:.2f}. This category has "
                    f"been trending upward. Try to reduce it back to average "
                    f"to save {excess:.2f}/month."
                ),
                "estimated_monthly_savings": excess,
                "priority": "medium" if excess < 1000 else "high",
            })

    return _sort_by_savings_desc(recs)


def _dedupe_and_sort_recs(savings_recs):
    """Keep the highest-savings rec per title, then order by priority
    (high first), then by savings within each priority.
    """
    seen_titles = set()
    deduped = []
    for r in sorted(savings_recs, key=lambda x: -x["estimated_monthly_savings"]):
        if r["title"] not in seen_titles:
            seen_titles.add(r["title"])
            deduped.append(r)

    deduped.sort(key=lambda r: (PRIORITY_ORDER.get(r["priority"], 3), -r["estimated_monthly_savings"]))
    return deduped


# ---------------------------------------------------------------------------
# Spend Optimization
# ---------------------------------------------------------------------------

def _build_spend_optimization(cat_stats, overall):
    """Build the spend optimization section."""
    if not cat_stats:
        return None

    sorted_cats = sorted(cat_stats.items(), key=lambda x: -x[1]["avg_monthly"])

    top_categories = []
    for cat, stats in sorted_cats[:5]:
        cur, avg = stats["current_month"], stats["avg_monthly"]
        mom_change = round(((cur - avg) / avg) * 100, 1) if avg > 0 else 0.0
        top_categories.append({
            "category": cat,
            "avg_monthly_spend": avg,
            "current_month_spend": cur,
            "month_over_month_change_percent": mom_change,
            "trend": stats["trend"],
        })

    rising = [
        {"category": cat, "avg_monthly": s["avg_monthly"], "current_month": s["current_month"]}
        for cat, s in sorted_cats
        if s["trend"] == "rising" and s["avg_monthly"] >= MIN_CATEGORY_SPEND
    ]

    return {
        "monthly_expense_avg": overall["avg_monthly_expense"],
        "current_month_expense": overall["current_month_expense"],
        "monthly_income_avg": overall["avg_monthly_income"],
        "top_categories": top_categories if top_categories else None,
        "rising_spend_categories": rising if rising else None,
    }


# ---------------------------------------------------------------------------
# Goal Insights — one narrative builder per goal status
# ---------------------------------------------------------------------------

def _insight_achieved(goal_name, target):
    insight = (
        f"Congratulations! You've achieved your '{goal_name}' goal! "
        f"Target of {target:.2f} has been met."
    )
    action_items = ["Consider setting a new, bigger goal to keep your momentum going."]
    return insight, action_items, None


def _insight_on_track(goal_name, target, predicted, allocated, progress, trend):
    insight = (
        f"You're on track to reach '{goal_name}' "
        f"(target: {target:.2f}) by {predicted}. "
        f"Keep saving {allocated:.2f}/month. "
        f"You've already covered {progress:.1f}% of this goal."
    )
    action_items = []
    if trend == "increasing":
        action_items.append(
            "Your savings trend is increasing — you might hit this goal even earlier."
        )
    action_items.append(f"Continue your current savings habit of {allocated:.2f}/month.")
    return insight, action_items, None


def _insight_at_risk(goal_name, required, allocated, progress, remaining, months_rem, total_potential):
    shortfall = round(required - allocated, 2)
    insight = (
        f"'{goal_name}' is at risk. You need {required:.2f}/month "
        f"but only {allocated:.2f}/month is allocated "
        f"(shortfall: {shortfall:.2f}/month). "
        f"You've completed {progress:.1f}% so far with {remaining:.2f} remaining."
    )

    action_items = []
    if total_potential >= shortfall:
        action_items.append(
            f"Following our savings recommendations could free up "
            f"{total_potential:.2f}/month — enough to cover the shortfall."
        )
    else:
        action_items.append(
            f"Try to increase your monthly savings by {shortfall:.2f} "
            f"through expense cuts or additional income."
        )
    if months_rem > 0:
        action_items.append(
            f"You have {months_rem} months left. Every month of delay "
            f"increases the required monthly savings."
        )
    return insight, action_items, None


def _insight_off_track(goal_name, target, remaining, progress, months_rem,
                        allocated, avg_savings, required, total_potential):
    if allocated > 0 and remaining > 0:
        months_needed = round(remaining / allocated)
        extra_time = max(0, months_needed - months_rem)
        insight = (
            f"'{goal_name}' won't be met by its deadline. "
            f"At the current allocated rate of {allocated:.2f}/month, "
            f"it will take approximately {months_needed} months "
            f"({extra_time} months beyond the deadline). "
            f"Progress: {progress:.1f}%, remaining: {remaining:.2f}."
        )
    elif avg_savings <= 0:
        extra_time = None
        insight = (
            f"'{goal_name}' is off track because your net savings are "
            f"currently negative or zero. You need a positive savings "
            f"rate to make progress. Remaining: {remaining:.2f}."
        )
    else:
        months_needed = round(remaining / avg_savings)
        extra_time = max(0, months_needed - months_rem) if months_rem > 0 else months_needed
        insight = (
            f"'{goal_name}' is off track. At your average savings rate "
            f"of {avg_savings:.2f}/month, it would take ~{months_needed} months. "
            f"Deadline is in {months_rem} months. Remaining: {remaining:.2f}."
        )

    action_items = []
    if total_potential > 0:
        boosted_monthly = allocated + total_potential
        if boosted_monthly > 0:
            boosted_months = round(remaining / boosted_monthly)
            action_items.append(
                f"By implementing all savings recommendations "
                f"(+{total_potential:.2f}/month), you could bring the timeline "
                f"down to ~{boosted_months} months."
            )
    action_items.append(
        f"Consider extending the deadline or reducing the target amount "
        f"from {target:.2f} to a more achievable level."
    )
    if required > 0:
        action_items.append(f"To stay on deadline, you would need {required:.2f}/month.")

    return insight, action_items, extra_time


def _insight_deadline_passed(goal_name, remaining, target, progress, avg_savings):
    insight = (
        f"The deadline for '{goal_name}' has passed. "
        f"You still need {remaining:.2f} to reach the target of {target:.2f} "
        f"({progress:.1f}% completed). "
    )
    action_items = []
    if avg_savings > 0:
        months_to_finish = round(remaining / avg_savings)
        insight += f"At your current savings rate, it would take ~{months_to_finish} more months."
        action_items.append(
            f"Set a new deadline {months_to_finish} months from now to stay motivated."
        )
    else:
        action_items.append(
            "Focus on building a positive savings rate first, then set a new deadline."
        )
    return insight, action_items, None


def _build_goal_insight(f, avg_savings, trend, total_potential):
    """Dispatch to the right narrative builder based on the goal's status.

    Returns (insight, action_items, extra_time_needed_months).
    """
    status = f["status"]
    goal_name = f["goal_name"]
    target = f["target_amount"]
    remaining = f["remaining_amount"]
    progress = f["progress_percent"]
    months_rem = f["months_remaining"]
    allocated = f.get("allocated_monthly_savings", 0)
    required = f.get("required_monthly_savings", 0)
    predicted = f.get("predicted_achievement_date")

    if status == "achieved":
        return _insight_achieved(goal_name, target)
    if status == "on_track":
        return _insight_on_track(goal_name, target, predicted, allocated, progress, trend)
    if status == "at_risk":
        return _insight_at_risk(goal_name, required, allocated, progress, remaining, months_rem, total_potential)
    if status == "off_track":
        return _insight_off_track(
            goal_name, target, remaining, progress, months_rem,
            allocated, avg_savings, required, total_potential,
        )
    if status == "deadline_passed":
        return _insight_deadline_passed(goal_name, remaining, target, progress, avg_savings)

    return f"'{goal_name}': Status unknown.", [], None


def _build_goal_insights(forecast_data, savings_recs):
    """Generate personalised natural-language insights for each goal."""
    if forecast_data is None:
        return None

    forecasts = forecast_data.get("forecasts")
    if not forecasts:
        return None

    savings_summary = forecast_data.get("savings_summary", {})
    avg_savings = savings_summary.get("avg_monthly_savings", 0)
    trend = savings_summary.get("savings_trend", "stable")
    allocation = forecast_data.get("allocation_plan", {})
    achievable = allocation.get("achievable_goals", 0)
    total_goals = allocation.get("total_goals", 0)

    total_potential = sum(r.get("estimated_monthly_savings", 0) for r in savings_recs)

    insights = []
    for f in forecasts:
        insight, action_items, extra_time = _build_goal_insight(f, avg_savings, trend, total_potential)
        insights.append({
            "goal_id": f["goal_id"],
            "goal_name": f["goal_name"],
            "status": f["status"],
            "progress_percent": f["progress_percent"],
            "insight": insight,
            "action_items": action_items if action_items else None,
            "extra_time_needed_months": extra_time,
        })

    # Add a portfolio-level insight
    if total_goals > 0:
        portfolio_msg = (
            f"Overall: {achievable} of {total_goals} goals are achievable "
            f"within their deadlines at your current savings rate of "
            f"{avg_savings:.2f}/month."
        )
        if trend == "increasing":
            portfolio_msg += " Your savings trend is positive — keep it up!"
        elif trend == "decreasing":
            portfolio_msg += (
                " However, your savings rate is declining. "
                "Review recent spending to get back on track."
            )

        insights.insert(0, {
            "goal_id": None,
            "goal_name": "Portfolio Summary",
            "status": "summary",
            "progress_percent": None,
            "insight": portfolio_msg,
            "action_items": None,
            "extra_time_needed_months": None,
        })

    return insights


# ---------------------------------------------------------------------------
# LLM Context Assembly
# ---------------------------------------------------------------------------

def _get_user_profile(user_id, user_obj=None):
    """Return (username, account_age_months).

    Parameters
    ----------
    user_obj : User | None
        When supplied (e.g. passed down from the Celery task that already
        fetched the row) the DB is not hit again.  Falls back to a
        ``User.objects.get`` lookup when *None*.
    """
    if user_obj is not None:
        today = date.today()
        account_age_months = (
            (today.year - user_obj.created_at.year) * 12
            + (today.month - user_obj.created_at.month)
        )
        return user_obj.username, account_age_months

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return "User", 0

    today = date.today()
    account_age_months = (
        (today.year - user.created_at.year) * 12 + (today.month - user.created_at.month)
    )
    return user.username, account_age_months


def _flatten_anomaly_summary(anomaly_data):
    """Reduce anomaly data to just the fields the LLM prompt needs."""
    if not anomaly_data or anomaly_data.get("insufficient_data"):
        return None

    summary = {}
    for period in ANOMALY_PERIOD_KEYS:
        items = anomaly_data.get(period)
        if items:
            summary[period] = [
                {
                    "title": a.get("title", ""),
                    "amount": a.get("amount", 0),
                    "category": a.get("category", ""),
                    "anomaly_score": a.get("anomaly_score", 0),
                }
                for a in items
            ]
    return summary


def _flatten_recurring_summary(recurring_data):
    """Reduce recurring-pattern data to just the fields the LLM prompt needs."""
    if not recurring_data:
        return None

    summary = []
    for bucket_key in RECURRING_BUCKET_KEYS:
        for p in recurring_data.get(bucket_key) or []:
            summary.append({
                "title": p.get("title", ""),
                "amount": float(p.get("amount", 0)),
                "mean_gap_days": p.get("mean_gap_days", 30),
                "recurring_type": p.get("recurring_type", "unknown"),
            })
    return summary


def _build_llm_context(user_id, cat_stats, overall, savings_recs,
                       spend_opt, forecast_data, anomaly_data,
                       recurring_data, user_obj=None):
    """
    Assemble a structured context dict that feeds the LLM prompt.

    This is the bridge between the rule engine outputs and the LLM —
    every piece of data the LLM needs is collected here so the prompt
    builder doesn't touch Django models or ML utilities directly.
    """
    username, account_age_months = _get_user_profile(user_id, user_obj=user_obj)
    total_potential = sum(r.get("estimated_monthly_savings", 0) for r in savings_recs)

    return {
        "user_profile": {
            "username": username,
            "account_age_months": account_age_months,
            "analysis_date": date.today().isoformat(),
        },
        "financial_snapshot": overall if overall else {},
        "savings_recommendations": savings_recs,
        "total_potential_savings": round(total_potential, 2),
        "spend_optimization": spend_opt,
        "goal_forecasts": forecast_data,
        "anomaly_summary": _flatten_anomaly_summary(anomaly_data),
        "recurring_summary": _flatten_recurring_summary(recurring_data),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_recommendations(user_id: int, *, recurring_data=None,
                              anomaly_data=None, forecast_data=None,
                              transactions=None, user_obj=None):
    """
    Generate personalised recommendations and insights for the user
    by synthesising outputs from all ML engines.

    Parameters
    ----------
    recurring_data, anomaly_data, forecast_data : dict, optional
        Pre-computed results from the other ML engines.  When supplied
        the corresponding engine is **not** re-invoked, avoiding
        duplicate work when the caller has already run them.
    transactions : list[dict] | None
        Pre-fetched 12-month transaction rows (amount, date,
        transaction_type, category).  When supplied the function
        skips its own DB query for spending analysis.
    user_obj : User | None
        Django User instance.  When supplied the function skips the
        ``User.objects.get`` call inside ``_get_user_profile``.

    Returns
    -------
    dict with "savings_opportunities", "spend_optimization", "goal_insights"
    or None if no transaction data exists.
    """

    # 1. Gather data from existing engines (skip if already provided)
    # if recurring_data is None:
    #     recurring_data = detect_recurring_transactions(user_id)
    if anomaly_data is None:
        anomaly_data = detect_anomalies(user_id)
    if forecast_data is None:
        forecast_data = forecast_goals(user_id)

    # 2. Compute category-level spending analysis
    # Pass pre-fetched transactions when available to avoid a duplicate DB call
    cat_stats, overall = _compute_category_monthly_spend(user_id, txns=transactions)

    if not cat_stats and not forecast_data:
        return None

    # 3. Generate savings recommendations
    savings_recs = []
    savings_recs.extend(_subscription_recommendations(recurring_data))
    savings_recs.extend(_anomaly_based_recommendations(anomaly_data, cat_stats))
    savings_recs.extend(_discretionary_cut_recommendations(cat_stats))
    savings_recs.extend(_trend_based_recommendations(cat_stats, overall))
    savings_recs = _dedupe_and_sort_recs(savings_recs)

    total_potential = sum(r["estimated_monthly_savings"] for r in savings_recs)

    # 4. Build spend optimization section
    spend_opt = _build_spend_optimization(cat_stats, overall)

    # 5. Build goal insights
    goal_insights = _build_goal_insights(forecast_data, savings_recs)

    # 6. Generate LLM narrative
    llm_insights = None
    try:
        llm_context = _build_llm_context(
            user_id, cat_stats, overall, savings_recs,
            spend_opt, forecast_data, anomaly_data, recurring_data,
            user_obj=user_obj,
        )
        llm_insights = generate_narrative(llm_context)
    except Exception as e:
        logger.error("LLM narrative generation failed — falling back to rule-based: %s", e)
        llm_insights = None

    # 7. Assemble response
    return {
        "savings_opportunities": {
            "total_potential_monthly_savings": round(total_potential, 2),
            "recommendations": savings_recs if savings_recs else None,
        } if savings_recs else None,
        "spend_optimization": spend_opt,
        "goal_insights": goal_insights,
        "llm_insights": llm_insights,
    }