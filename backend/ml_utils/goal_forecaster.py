
from collections import defaultdict
from datetime import date, timedelta
from math import ceil
from statistics import mean, stdev

from finance.models import Transaction, Goal


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_MONTHS_FOR_TREND = 3   # need ≥ 3 months of data for trend analysis

# Scenario multipliers — how much of the standard deviation to add/subtract
OPTIMISTIC_SIGMA = 1.0        # avg + 1σ  (or trend-boosted)
PESSIMISTIC_SIGMA = 1.0       # avg − 1σ  (floored at 10 % of avg)
PESSIMISTIC_FLOOR_PCT = 0.10  # never project below 10 % of avg savings

STATUS_SORT_ORDER = {"achieved": 0, "on_track": 1, "at_risk": 2, "off_track": 3, "deadline_passed": 4}


# ---------------------------------------------------------------------------
# Savings-history helpers
# ---------------------------------------------------------------------------

def _compute_monthly_savings(expenses_and_income):
    """Bucket transactions by (year, month) and net income vs. expense.

    Returns (monthly_nets, total_income, total_expense) where monthly_nets is
    a list of (year, month, net_savings) sorted chronologically.
    """
    monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    total_income = 0.0
    total_expense = 0.0

    for txn in expenses_and_income:
        key = (txn["date"].year, txn["date"].month)
        amt = float(txn["amount"])
        if txn["transaction_type"] == "Income":
            monthly[key]["income"] += amt
            total_income += amt
        else:
            monthly[key]["expense"] += amt
            total_expense += amt

    monthly_nets = sorted(
        (year, month, vals["income"] - vals["expense"])
        for (year, month), vals in monthly.items()
    )
    return monthly_nets, total_income, total_expense


def _linear_regression_slope(values):
    """Simple OLS slope for values indexed 0..n-1 (positive = increasing)."""
    n = len(values)
    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2.0
    y_mean = mean(values)
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _classify_trend(slope, avg):
    """Classify savings trend as increasing, stable, or decreasing."""
    if avg == 0:
        return "stable"
    relative_slope = slope / abs(avg)
    if relative_slope > 0.05:
        return "increasing"
    if relative_slope < -0.05:
        return "decreasing"
    return "stable"


def _compute_savings_stats(monthly_nets):
    """Derive (avg_monthly_savings, savings_std, savings_trend) from the
    monthly net-savings history.
    """
    if not monthly_nets:
        return 0.0, 0.0, "stable"

    net_values = [net for _, _, net in monthly_nets]
    avg = mean(net_values)
    std = stdev(net_values) if len(net_values) >= 2 else 0.0

    if len(net_values) >= MIN_MONTHS_FOR_TREND:
        trend = _classify_trend(_linear_regression_slope(net_values), avg)
    else:
        trend = "stable"

    return avg, std, trend


def _compute_confidence(avg_monthly_savings, savings_std):
    """Confidence score based on how consistent monthly savings has been."""
    if avg_monthly_savings > 0 and savings_std > 0:
        return round(max(0.0, min(1.0, 1.0 - (savings_std / avg_monthly_savings))), 2)
    if avg_monthly_savings > 0:
        return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _months_between(d1, d2):
    """Number of calendar months from d1 to d2 (can be negative)."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _add_months(start_date, months):
    """Return a date that is `months` months after start_date."""
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, 28)  # safe day, avoids month-length issues
    return date(year, month, day)


# ---------------------------------------------------------------------------
# Scenario / projection helpers
# ---------------------------------------------------------------------------

def _compute_scenario_rates(avg_monthly_savings, savings_std, savings_trend):
    """
    Return (optimistic, realistic, pessimistic) monthly savings rates.

    * Optimistic  = avg + 1σ  (boosted further if trend is 'increasing')
    * Realistic   = avg       (nudged slightly by trend direction)
    * Pessimistic = avg − 1σ  (floored so it never drops below 10 % of avg)
    """
    avg, std = avg_monthly_savings, savings_std

    if savings_trend == "increasing":
        trend_bonus = 0.05    # +5 % on optimistic / realistic
    elif savings_trend == "decreasing":
        trend_bonus = -0.05   # −5 % on realistic, extra penalty pessimistic
    else:
        trend_bonus = 0.0

    optimistic = avg + OPTIMISTIC_SIGMA * std + avg * max(trend_bonus, 0)
    realistic = avg + avg * trend_bonus
    pessimistic = avg - PESSIMISTIC_SIGMA * std + avg * min(trend_bonus, 0)

    # Floor pessimistic so it never goes below 10 % of avg (or 0 if avg <= 0)
    if avg > 0:
        pessimistic = max(pessimistic, avg * PESSIMISTIC_FLOOR_PCT)
    else:
        pessimistic = min(pessimistic, 0.0)

    return round(optimistic, 2), round(realistic, 2), round(pessimistic, 2)


def _project_scenario(rate, label, remaining_amount, today):
    """Single scenario projection: rate/months/estimated completion date."""
    if rate <= 0 or remaining_amount <= 0:
        return {
            "scenario": label,
            "monthly_savings_rate": round(rate, 2),
            "months_to_goal": None,
            "estimated_completion_date": None,
        }

    months = ceil(remaining_amount / rate)
    completion = _add_months(today, months)
    return {
        "scenario": label,
        "monthly_savings_rate": round(rate, 2),
        "months_to_goal": months,
        "estimated_completion_date": completion.isoformat(),
    }


def _build_projections(remaining_amount, optimistic_rate, realistic_rate, pessimistic_rate, today):
    """Build the optimistic / realistic / pessimistic projection list for a goal."""
    return [
        _project_scenario(optimistic_rate, "optimistic", remaining_amount, today),
        _project_scenario(realistic_rate, "realistic", remaining_amount, today),
        _project_scenario(pessimistic_rate, "pessimistic", remaining_amount, today),
    ]


def _zero_projections(today_str):
    """The (already-achieved-goal) special case: all scenarios at zero."""
    return [
        {"scenario": scenario, "monthly_savings_rate": 0.0,
         "months_to_goal": 0, "estimated_completion_date": today_str}
        for scenario in ("optimistic", "realistic", "pessimistic")
    ]


# ---------------------------------------------------------------------------
# Allocation helper
# ---------------------------------------------------------------------------

def _greedy_allocate(goals_with_requirements, total_budget):
    """Fund the cheapest (lowest required-monthly) goals first until the
    monthly savings budget runs out. Returns {goal_id: allocated_amount}.
    """
    sorted_goals = sorted(goals_with_requirements, key=lambda g: g["required_monthly"])

    allocations = {}
    remaining_budget = max(total_budget, 0.0)

    for goal in sorted_goals:
        needed = goal["required_monthly"]
        if needed <= 0:
            # Goal already achieved or no remaining amount
            allocations[goal["goal_id"]] = 0.0
        elif needed <= remaining_budget:
            allocations[goal["goal_id"]] = round(needed, 2)
            remaining_budget -= needed
        else:
            # Partial funding — allocate whatever is left
            allocations[goal["goal_id"]] = round(remaining_budget, 2)
            remaining_budget = 0.0

    return allocations


# ---------------------------------------------------------------------------
# Per-goal status helper
# ---------------------------------------------------------------------------

def _evaluate_pending_goal(remaining_amount, deadline_str, months_remaining, allocated, required, today):
    """Work out a still-pending goal's status given its allocated savings.

    Returns (status, on_track, predicted_date_str, counts_as_achievable).
    """
    if allocated > 0:
        months_to_goal = ceil(remaining_amount / allocated)
        predicted_date = _add_months(today, months_to_goal)
        predicted_date_str = predicted_date.isoformat()
        on_track = predicted_date <= date.fromisoformat(deadline_str)
    else:
        predicted_date = None
        predicted_date_str = None
        on_track = False

    if on_track and allocated >= required:
        return "on_track", on_track, predicted_date_str, True

    if on_track:
        # Funded, but tightly — check if within 1.0x remaining time
        deadline_date = date.fromisoformat(deadline_str)
        if predicted_date and months_remaining > 0:
            ratio = (predicted_date - today).days / max((deadline_date - today).days, 1)
            if ratio > 1.0:
                return "at_risk", on_track, predicted_date_str, False
            return "on_track", on_track, predicted_date_str, True
        return "at_risk", on_track, predicted_date_str, False

    return "off_track", on_track, predicted_date_str, False


# ---------------------------------------------------------------------------
# Forecast entry builders (one per goal status)
# ---------------------------------------------------------------------------

def _forecast_for_achieved_goal(g, today):
    return {
        **g,
        "allocated_monthly_savings": 0.0,
        "required_monthly_savings": 0.0,
        "predicted_achievement_date": today.isoformat(),
        "on_track": True,
        "confidence": 1.0,
        "projections": _zero_projections(today.isoformat()),
    }


def _forecast_for_missed_deadline_goal(g, optimistic_rate, realistic_rate, pessimistic_rate, today):
    # Still show projections so the user knows when they *could* finish
    projections = _build_projections(
        g["remaining_amount"], optimistic_rate, realistic_rate, pessimistic_rate, today,
    )
    return {
        **g,
        "allocated_monthly_savings": 0.0,
        "required_monthly_savings": g["remaining_amount"],  # impossible now
        "predicted_achievement_date": None,
        "on_track": False,
        "confidence": 0.0,
        "projections": projections,
    }


def _forecast_for_pending_goal(g, allocated, required, confidence,
                                optimistic_rate, realistic_rate, pessimistic_rate, today):
    status, on_track, predicted_date_str, is_achievable = _evaluate_pending_goal(
        g["remaining_amount"], g["deadline"], g["months_remaining"], allocated, required, today,
    )
    g["status"] = status

    projections = _build_projections(
        g["remaining_amount"], optimistic_rate, realistic_rate, pessimistic_rate, today,
    )

    forecast = {
        **g,
        "allocated_monthly_savings": allocated,
        "required_monthly_savings": round(required, 2),
        "predicted_achievement_date": predicted_date_str,
        "on_track": on_track,
        "confidence": confidence,
        "projections": projections,
    }
    return forecast, is_achievable


# ---------------------------------------------------------------------------
# Main forecasting function
# ---------------------------------------------------------------------------

def forecast_goals(user_id: int):
    # ------------------------------------------------------------------
    # 1. Fetch goals
    # ------------------------------------------------------------------
    goals = list(
        Goal.objects
        .filter(user_id=user_id)
        .values("id", "name", "target_amount", "deadline")
    )
    if not goals:
        return None

    # ------------------------------------------------------------------
    # 2. Fetch transactions up to end of last month and compute savings
    #    metrics.  The current (in-progress) month is intentionally
    #    excluded so partial-month figures don't skew the baseline.
    # ------------------------------------------------------------------
    today = date.today()
    last_month_end = date(today.year, today.month, 1) - timedelta(days=1)

    all_transactions = list(
        Transaction.objects
        .filter(user_id=user_id, date__lte=last_month_end)
        .order_by("date")
        .values("id", "amount", "date", "transaction_type")
    )

    monthly_nets, total_income, total_expense = _compute_monthly_savings(all_transactions)
    total_savings = total_income - total_expense

    # Limit to maximum last 12 months of data if the user has more than 12 months of data
    baseline_nets = monthly_nets
    if len(monthly_nets) > 12:
        baseline_nets = monthly_nets[-12:]

    avg_monthly_savings, savings_std, savings_trend = _compute_savings_stats(baseline_nets)
    optimistic_rate, realistic_rate, pessimistic_rate = _compute_scenario_rates(
        avg_monthly_savings, savings_std, savings_trend,
    )
    confidence = _compute_confidence(avg_monthly_savings, savings_std)

    # ------------------------------------------------------------------
    # 3. Classify goals and prepare for allocation
    # ------------------------------------------------------------------
    # today is already set above; re-use it for deadline calculations
    goal_data = []

    for goal in goals:
        target = float(goal["target_amount"])
        deadline = goal["deadline"]
        remaining = max(0.0, target - total_savings)
        progress = min(100.0, (total_savings / target) * 100.0) if target > 0 else 100.0
        months_rem = _months_between(today, deadline)

        g = {
            "goal_id": goal["id"],
            "goal_name": goal["name"],
            "target_amount": target,
            "deadline": deadline.isoformat(),
            "current_savings": round(total_savings, 2),
            "remaining_amount": round(remaining, 2),
            "progress_percent": round(progress, 2),
            "months_remaining": months_rem,
        }

        # Pre-classify terminal states
        if total_savings >= target:
            g["status"] = "achieved"
        elif months_rem <= 0:
            g["status"] = "deadline_passed"
        else:
            g["status"] = "pending"  # will be updated after allocation
            g["required_monthly"] = remaining / months_rem

        goal_data.append(g)

    # ------------------------------------------------------------------
    # 4. Run greedy allocation on active (pending) goals
    # ------------------------------------------------------------------
    pending_goals = [g for g in goal_data if g["status"] == "pending"]
    allocations = _greedy_allocate(
        [{"goal_id": g["goal_id"], "required_monthly": g["required_monthly"]} for g in pending_goals],
        avg_monthly_savings,
    )

    # ------------------------------------------------------------------
    # 5. Build per-goal forecasts
    # ------------------------------------------------------------------
    achievable_count = 0
    forecasts = []

    for g in goal_data:
        if g["status"] == "achieved":
            forecasts.append(_forecast_for_achieved_goal(g, today))
            achievable_count += 1

        elif g["status"] == "deadline_passed":
            forecasts.append(_forecast_for_missed_deadline_goal(
                g, optimistic_rate, realistic_rate, pessimistic_rate, today,
            ))

        else:  # pending
            allocated = allocations.get(g["goal_id"], 0.0)
            required = g.pop("required_monthly", 0.0)
            forecast, is_achievable = _forecast_for_pending_goal(
                g, allocated, required, confidence,
                optimistic_rate, realistic_rate, pessimistic_rate, today,
            )
            forecasts.append(forecast)
            if is_achievable:
                achievable_count += 1

    # Sort forecasts: on_track first, then by progress descending
    forecasts.sort(key=lambda f: (STATUS_SORT_ORDER.get(f["status"], 5), -f["progress_percent"]))

    # ------------------------------------------------------------------
    # 6. Build response
    # ------------------------------------------------------------------
    total_goals = len(goal_data)
    total_allocated = sum(allocations.values())
    budget_util = (total_allocated / avg_monthly_savings * 100.0) if avg_monthly_savings > 0 else 0.0

    return {
        "savings_summary": {
            "avg_monthly_savings": round(avg_monthly_savings, 2),
            "savings_trend": savings_trend,
            "total_savings": round(total_savings, 2),
        },
        "allocation_plan": {
            "total_goals": total_goals,
            "achievable_goals": achievable_count,
            "budget_utilization_percent": round(budget_util, 2),
        },
        "forecasts": forecasts if forecasts else None,
    }