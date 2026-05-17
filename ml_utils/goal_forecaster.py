
from collections import defaultdict
from datetime import date
from math import ceil
from statistics import mean, stdev

from finance.models import Transaction, Goal


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_MONTHS_FOR_TREND = 3   # need ≥ 3 months of data for trend analysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_monthly_savings(expenses_and_income):
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

    # Sort by (year, month)
    monthly_nets = sorted(
        [(y, m, vals["income"] - vals["expense"]) for (y, m), vals in monthly.items()]
    )
    return monthly_nets, total_income, total_expense


def _linear_regression_slope(values):
    """
    Simple OLS slope for a list of numeric values indexed 0..n-1.
    Returns the slope (positive = increasing, negative = decreasing).
    """
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
    elif relative_slope < -0.05:
        return "decreasing"
    return "stable"


def _months_between(d1, d2):
    """Return the number of calendar months from d1 to d2 (can be negative)."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _add_months(start_date, months):
    """Return a date that is `months` months after start_date."""
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, 28)  # safe day
    return date(year, month, day)


def _greedy_allocate(goals_with_requirements, total_budget):
    
    # Sort by required monthly amount ascending (cheapest first)
    sorted_goals = sorted(goals_with_requirements, key=lambda g: g["required_monthly"])

    allocations = {}
    remaining_budget = max(total_budget, 0.0)

    for goal in sorted_goals:
        needed = goal["required_monthly"]
        if needed <= 0:
            # Goal already achieved or no remaining amount
            allocations[goal["goal_id"]] = 0.0
            continue

        if needed <= remaining_budget:
            # Fully fund this goal
            allocations[goal["goal_id"]] = round(needed, 2)
            remaining_budget -= needed
        else:
            # Partial funding — allocate whatever is left
            allocations[goal["goal_id"]] = round(remaining_budget, 2)
            remaining_budget = 0.0

    return allocations


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
    # 2. Fetch all transactions and compute savings metrics
    # ------------------------------------------------------------------
    all_transactions = list(
        Transaction.objects
        .filter(user_id=user_id)
        .order_by("date")
        .values("id", "amount", "date", "transaction_type")
    )

    monthly_nets, total_income, total_expense = _compute_monthly_savings(all_transactions)
    total_savings = total_income - total_expense

    # Monthly savings stats
    if monthly_nets:
        net_values = [net for _, _, net in monthly_nets]
        avg_monthly_savings = mean(net_values)

        if len(net_values) >= 2:
            savings_std = stdev(net_values)
        else:
            savings_std = 0.0

        if len(net_values) >= MIN_MONTHS_FOR_TREND:
            slope = _linear_regression_slope(net_values)
            savings_trend = _classify_trend(slope, avg_monthly_savings)
        else:
            savings_trend = "stable"
    else:
        avg_monthly_savings = 0.0
        savings_std = 0.0
        savings_trend = "stable"

    # Confidence based on savings consistency
    if avg_monthly_savings > 0 and savings_std > 0:
        confidence = round(max(0.0, min(1.0, 1.0 - (savings_std / avg_monthly_savings))), 2)
    elif avg_monthly_savings > 0:
        confidence = 1.0
    else:
        confidence = 0.0

    # ------------------------------------------------------------------
    # 3. Classify goals and prepare for allocation
    # ------------------------------------------------------------------
    today = date.today()
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
        [{"goal_id": g["goal_id"],
          "required_monthly": g["required_monthly"],
          "months_remaining": g["months_remaining"],
          "remaining_amount": g["remaining_amount"]}
         for g in pending_goals],
        avg_monthly_savings,
    )

    # ------------------------------------------------------------------
    # 5. Build per-goal forecasts
    # ------------------------------------------------------------------
    achievable_count = 0
    forecasts = []

    for g in goal_data:
        gid = g["goal_id"]

        if g["status"] == "achieved":
            forecasts.append({
                **g,
                "allocated_monthly_savings": 0.0,
                "required_monthly_savings": 0.0,
                "predicted_achievement_date": today.isoformat(),
                "on_track": True,
                "confidence": 1.0,
            })
            achievable_count += 1
            continue

        if g["status"] == "deadline_passed":
            forecasts.append({
                **g,
                "allocated_monthly_savings": 0.0,
                "required_monthly_savings": g["remaining_amount"],  # impossible now
                "predicted_achievement_date": None,
                "on_track": False,
                "confidence": 0.0,
            })
            continue

        # Pending goals — use allocation results
        allocated = allocations.get(gid, 0.0)
        required = g.pop("required_monthly", 0.0)

        # Predicted achievement date based on allocated amount
        if allocated > 0:
            months_to_goal = ceil(g["remaining_amount"] / allocated)
            predicted_date = _add_months(today, months_to_goal)
            predicted_date_str = predicted_date.isoformat()
            on_track = predicted_date <= date.fromisoformat(g["deadline"])
        else:
            predicted_date = None
            predicted_date_str = None
            on_track = False

        # Determine status
        if on_track and allocated >= required:
            status = "on_track"
            achievable_count += 1
        elif on_track:
            # Funded but tightly — check if within 1.25× remaining time
            if predicted_date and g["months_remaining"] > 0:
                ratio = (predicted_date - today).days / max(
                    (date.fromisoformat(g["deadline"]) - today).days, 1
                )
                if ratio > 1.0:
                    status = "at_risk"
                else:
                    status = "on_track"
                    achievable_count += 1
            else:
                status = "at_risk"
        else:
            status = "off_track"

        g["status"] = status
        forecasts.append({
            **g,
            "allocated_monthly_savings": allocated,
            "required_monthly_savings": round(required, 2),
            "predicted_achievement_date": predicted_date_str,
            "on_track": on_track,
            "confidence": confidence,
        })

    # Sort forecasts: on_track first, then by progress descending
    status_order = {"achieved": 0, "on_track": 1, "at_risk": 2, "off_track": 3, "deadline_passed": 4}
    forecasts.sort(key=lambda f: (status_order.get(f["status"], 5), -f["progress_percent"]))

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
