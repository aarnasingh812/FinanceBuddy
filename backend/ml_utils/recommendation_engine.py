import logging
from collections import defaultdict
from datetime import date
from statistics import mean

from finance.models import Transaction, Goal, User
from ml_utils.recurring_detector import detect_recurring_transactions
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


# ---------------------------------------------------------------------------
# Helpers — Spending Analysis
# ---------------------------------------------------------------------------

def _compute_category_monthly_spend(user_id):
   
    today = date.today()
    current_ym = (today.year, today.month)

    txns = list(
        Transaction.objects
        .filter(user_id=user_id)
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
        avg_m = mean(totals) if totals else 0.0
        cur_m = monthly_map.get(current_ym, 0.0)

        # Trend: compare last month to average of prior months
        sorted_months = sorted(monthly_map.keys())
        if len(sorted_months) >= 3:
            recent = monthly_map[sorted_months[-1]]
            prior_avg = mean([monthly_map[k] for k in sorted_months[:-1]])
            if prior_avg > 0:
                change = (recent - prior_avg) / prior_avg
                trend = "rising" if change > 0.15 else ("falling" if change < -0.15 else "stable")
            else:
                trend = "stable"
        else:
            trend = "stable"

        cat_stats[cat] = {
            "monthly_totals": dict(monthly_map),
            "avg_monthly": round(avg_m, 2),
            "current_month": round(cur_m, 2),
            "trend": trend,
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


# ---------------------------------------------------------------------------
# Recommendation generators (each returns a list of rec dicts)
# ---------------------------------------------------------------------------

def _subscription_recommendations(recurring_data):
    """Suggest cancelling low-priority recurring subscriptions."""
    recs = []
    if not recurring_data:
        return recs

    for bucket_key in ("15_days", "30_days", "90_days"):
        patterns = recurring_data.get(bucket_key)
        if not patterns:
            continue
        for p in patterns:
            rtype = p.get("recurring_type", "")
            if rtype in ("Subscription", "Bill"):
                amt = float(p["amount"])
                # Normalise to monthly
                gap = p.get("mean_gap_days", 30)
                monthly_cost = round(amt * (30 / max(gap, 1)), 2)

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

    # Sort by savings descending
    recs.sort(key=lambda r: r["estimated_monthly_savings"], reverse=True)
    return recs


def _anomaly_based_recommendations(anomaly_data, cat_stats):
    """Suggest reducing spend in categories with anomalous transactions."""
    recs = []
    if not anomaly_data:
        return recs

    # Collect categories that triggered anomalies
    flagged_categories = defaultdict(float)
    for period in ("current_month", "last_3_months"):
        anomalies = anomaly_data.get(period)
        if not anomalies:
            continue
        for a in anomalies:
            cat = a.get("category", "")
            flagged_categories[cat] += float(a.get("amount", 0))

    for cat, total_flagged in sorted(flagged_categories.items(), key=lambda x: -x[1]):
        stats = cat_stats.get(cat, {})
        avg = stats.get("avg_monthly", 0)
        if avg < MIN_CATEGORY_SPEND:
            continue

        excess = round(total_flagged - avg, 2) if total_flagged > avg else 0
        if excess > 0:
            recs.append({
                "type": "anomaly_reduction",
                "title": f"Unusual spending in '{cat}'",
                "detail": (
                    f"Your recent anomalous transactions in '{cat}' totalled "
                    f"{total_flagged:.2f}, which is {excess:.2f} above your "
                    f"monthly average of {avg:.2f}. Keeping '{cat}' spending "
                    f"closer to average could save ~{excess:.2f}."
                ),
                "estimated_monthly_savings": excess,
                "priority": "high" if excess >= 1000 else "medium",
            })

    return recs


def _discretionary_cut_recommendations(cat_stats):
    """Suggest a percentage cut in top discretionary categories."""
    recs = []
    discretionary_cats = []

    for cat, stats in cat_stats.items():
        if _is_discretionary(cat) and stats["avg_monthly"] >= MIN_CATEGORY_SPEND:
            discretionary_cats.append((cat, stats))

    # Sort by avg_monthly descending
    discretionary_cats.sort(key=lambda x: -x[1]["avg_monthly"])

    # Take top 3
    for cat, stats in discretionary_cats[:3]:
        avg = stats["avg_monthly"]
        saving = round(avg * CUT_PERCENT / 100, 2)
        recs.append({
            "type": "discretionary_cut",
            "title": f"Reduce '{cat}' spending by {CUT_PERCENT}%",
            "detail": (
                f"You spend an average of {avg:.2f}/month on '{cat}'. "
                f"A {CUT_PERCENT}% reduction would save {saving:.2f}/month "
                f"without drastically changing your lifestyle."
            ),
            "estimated_monthly_savings": saving,
            "priority": "medium",
        })

    return recs


def _trend_based_recommendations(cat_stats, overall):
    """Flag categories with rising spend trends."""
    recs = []
    for cat, stats in cat_stats.items():
        if stats["trend"] == "rising" and stats["avg_monthly"] >= MIN_CATEGORY_SPEND:
            cur = stats["current_month"]
            avg = stats["avg_monthly"]
            excess = round(cur - avg, 2)
            if excess > 0:
                recs.append({
                    "type": "rising_trend",
                    "title": f"'{cat}' spending is rising",
                    "detail": (
                        f"Your '{cat}' spending this month ({cur:.2f}) is above "
                        f"your average ({avg:.2f}). This category has been trending "
                        f"upward. Bringing it back to average saves {excess:.2f}/month."
                    ),
                    "estimated_monthly_savings": excess,
                    "priority": "medium" if excess < 1000 else "high",
                })

    recs.sort(key=lambda r: r["estimated_monthly_savings"], reverse=True)
    return recs


# ---------------------------------------------------------------------------
# Spend Optimization
# ---------------------------------------------------------------------------

def _build_spend_optimization(cat_stats, overall):
    """Build the spend optimization section."""
    if not cat_stats:
        return None

    # Top spending categories
    sorted_cats = sorted(cat_stats.items(), key=lambda x: -x[1]["avg_monthly"])
    top_categories = []
    for cat, stats in sorted_cats[:5]:
        cur = stats["current_month"]
        avg = stats["avg_monthly"]
        if avg > 0:
            mom_change = round(((cur - avg) / avg) * 100, 1)
        else:
            mom_change = 0.0

        top_categories.append({
            "category": cat,
            "avg_monthly_spend": stats["avg_monthly"],
            "current_month_spend": stats["current_month"],
            "month_over_month_change_percent": mom_change,
            "trend": stats["trend"],
        })

    # Rising categories
    rising = [
        {"category": cat, "avg_monthly": s["avg_monthly"],
         "current_month": s["current_month"]}
        for cat, s in sorted_cats if s["trend"] == "rising" and s["avg_monthly"] >= MIN_CATEGORY_SPEND
    ]

    return {
        "monthly_expense_avg": overall["avg_monthly_expense"],
        "current_month_expense": overall["current_month_expense"],
        "monthly_income_avg": overall["avg_monthly_income"],
        "top_categories": top_categories if top_categories else None,
        "rising_spend_categories": rising if rising else None,
    }


# ---------------------------------------------------------------------------
# Goal Insights
# ---------------------------------------------------------------------------

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

    # Total potential savings from all recommendations
    total_potential = sum(r.get("estimated_monthly_savings", 0) for r in savings_recs)

    insights = []
    for f in forecasts:
        goal_name = f["goal_name"]
        status = f["status"]
        target = f["target_amount"]
        remaining = f["remaining_amount"]
        progress = f["progress_percent"]
        months_rem = f["months_remaining"]
        allocated = f.get("allocated_monthly_savings", 0)
        required = f.get("required_monthly_savings", 0)
        predicted = f.get("predicted_achievement_date")

        action_items = []
        extra_time = None

        if status == "achieved":
            insight = (
                f"Congratulations! You've achieved your '{goal_name}' goal! "
                f"Target of {target:.2f} has been met."
            )
            action_items.append(f"Consider setting a new, bigger goal to keep your momentum going.")

        elif status == "on_track":
            insight = (
                f"You're on track to reach '{goal_name}' "
                f"(target: {target:.2f}) by {predicted}. "
                f"Keep saving {allocated:.2f}/month. "
                f"You've already covered {progress:.1f}% of this goal."
            )
            if trend == "increasing":
                action_items.append(
                    f"Your savings trend is increasing — you might hit this goal even earlier."
                )
            action_items.append(f"Continue your current savings habit of {allocated:.2f}/month.")

        elif status == "at_risk":
            shortfall = round(required - allocated, 2)
            insight = (
                f"'{goal_name}' is at risk. You need {required:.2f}/month "
                f"but only {allocated:.2f}/month is allocated "
                f"(shortfall: {shortfall:.2f}/month). "
                f"You've completed {progress:.1f}% so far with {remaining:.2f} remaining."
            )
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

        elif status == "off_track":
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
                months_needed = round(remaining / avg_savings) if avg_savings > 0 else 0
                extra_time = max(0, months_needed - months_rem) if months_rem > 0 else months_needed
                insight = (
                    f"'{goal_name}' is off track. At your average savings rate "
                    f"of {avg_savings:.2f}/month, it would take ~{months_needed} months. "
                    f"Deadline is in {months_rem} months. Remaining: {remaining:.2f}."
                )

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
                action_items.append(
                    f"To stay on deadline, you would need {required:.2f}/month."
                )

        elif status == "deadline_passed":
            extra_time = None
            insight = (
                f"The deadline for '{goal_name}' has passed. "
                f"You still need {remaining:.2f} to reach the target of {target:.2f} "
                f"({progress:.1f}% completed). "
            )
            if avg_savings > 0:
                months_to_finish = round(remaining / avg_savings)
                insight += (
                    f"At your current savings rate, it would take ~{months_to_finish} "
                    f"more months."
                )
                action_items.append(
                    f"Set a new deadline {months_to_finish} months from now to stay motivated."
                )
            else:
                action_items.append(
                    "Focus on building a positive savings rate first, then set a new deadline."
                )

        else:
            insight = f"'{goal_name}': Status unknown."

        insights.append({
            "goal_id": f["goal_id"],
            "goal_name": goal_name,
            "status": status,
            "progress_percent": progress,
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

def _build_llm_context(user_id, cat_stats, overall, savings_recs,
                       spend_opt, forecast_data, anomaly_data,
                       recurring_data):
    """
    Assemble a structured context dict that feeds the LLM prompt.

    This is the bridge between the rule engine outputs and the LLM —
    every piece of data the LLM needs is collected here so the prompt
    builder doesn't touch Django models or ML utilities directly.
    """
    # --- User profile ---
    try:
        user = User.objects.get(id=user_id)
        username = user.username
        account_age_months = (
            (date.today().year - user.created_at.year) * 12
            + (date.today().month - user.created_at.month)
        )
    except User.DoesNotExist:
        username = "User"
        account_age_months = 0

    # --- Anomaly summary (flatten to key info only) ---
    anomaly_summary = None
    if anomaly_data and not anomaly_data.get("insufficient_data"):
        anomaly_summary = {}
        for period in ("current_month", "last_3_months"):
            items = anomaly_data.get(period)
            if items:
                anomaly_summary[period] = [
                    {
                        "title": a.get("title", ""),
                        "amount": a.get("amount", 0),
                        "category": a.get("category", ""),
                        "anomaly_score": a.get("anomaly_score", 0),
                    }
                    for a in items
                ]

    # --- Recurring summary (flatten) ---
    recurring_summary = None
    if recurring_data:
        recurring_summary = []
        for bucket_key in ("15_days", "30_days", "90_days"):
            patterns = recurring_data.get(bucket_key)
            if not patterns:
                continue
            for p in patterns:
                recurring_summary.append({
                    "title": p.get("title", ""),
                    "amount": float(p.get("amount", 0)),
                    "mean_gap_days": p.get("mean_gap_days", 30),
                    "recurring_type": p.get("recurring_type", "unknown"),
                })

    # --- Total potential savings ---
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
        "anomaly_summary": anomaly_summary,
        "recurring_summary": recurring_summary,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_recommendations(user_id: int):
    """
    Generate personalised recommendations and insights for the user
    by synthesising outputs from all ML engines.

    Returns
    -------
    dict with "savings_opportunities", "spend_optimization", "goal_insights"
    or None if no transaction data exists.
    """

    # 1. Gather data from existing engines
    recurring_data = detect_recurring_transactions(user_id)
    anomaly_data = detect_anomalies(user_id)
    forecast_data = forecast_goals(user_id)

    # 2. Compute category-level spending analysis
    cat_stats, overall = _compute_category_monthly_spend(user_id)

    if not cat_stats and not forecast_data:
        return None

    # 3. Generate savings recommendations
    savings_recs = []
    savings_recs.extend(_subscription_recommendations(recurring_data))
    savings_recs.extend(_anomaly_based_recommendations(anomaly_data, cat_stats))
    savings_recs.extend(_discretionary_cut_recommendations(cat_stats))
    savings_recs.extend(_trend_based_recommendations(cat_stats, overall))

    # Deduplicate by category (keep highest savings)
    seen_cats = set()
    deduped = []
    for r in sorted(savings_recs, key=lambda x: -x["estimated_monthly_savings"]):
        # Use title as dedup key
        if r["title"] not in seen_cats:
            seen_cats.add(r["title"])
            deduped.append(r)
    savings_recs = deduped

    # Re-sort: high priority first, then by savings
    priority_order = {"high": 0, "medium": 1, "low": 2}
    savings_recs.sort(
        key=lambda r: (priority_order.get(r["priority"], 3), -r["estimated_monthly_savings"])
    )

    # Compute total potential savings
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
