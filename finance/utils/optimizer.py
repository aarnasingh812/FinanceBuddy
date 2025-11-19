# finance/utils/optimizer.py

import math
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from scipy.stats import norm
from decimal import Decimal
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from finance.models import Transaction

# Config
DEFAULT_TARGET_PROB = 0.80  # desired probability of meeting goal
MIN_MONTHS_FOR_STATS = 3    # need at least this many months to compute reasonable mu/sigma
COLD_START_MONTHLY_SAVING = 100.0  # fallback suggestion (currency units) for new users
MIN_SAVING_BUFFER_PCT = 0.05  # keep a small buffer on top of computed x

def months_between(d1: date, d2: date) -> int:
    """Return number of full months between d1 and d2. If d2<=d1 returns 0."""
    if d2 <= d1:
        return 0
    rd = relativedelta(d2, d1)
    return rd.years * 12 + rd.months + (1 if rd.days > 0 else 0)

def compute_monthly_savings_stats(user):
    """
    Returns (mu, sigma, months_count, avg_income, avg_expense)
    mu: mean monthly savings (income - expense)
    sigma: stddev of monthly savings
    """
    qs = (
        Transaction.objects
        .filter(user=user)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(
                income=Sum("amount", filter=Q(transaction_type='Income')),
                expense=Sum("amount", filter=Q(transaction_type='Expense'))
                )

        .order_by("month")
    )
    df = pd.DataFrame(list(qs))

    if df.empty:
        return 0.0, 0.0, 0, 0.0, 0.0

    # fill NaN
    df['income'] = df['income'].fillna(0).apply(float)
    df['expense'] = df['expense'].fillna(0).apply(float)
    df['savings'] = df['income'] - df['expense']

    mu = float(df['savings'].mean())
    sigma = float(df['savings'].std(ddof=0)) if df.shape[0] > 1 else 0.0
    months_count = df.shape[0]
    avg_income = float(df['income'].mean())
    avg_expense = float(df['expense'].mean())
    return mu, sigma, months_count, avg_income, avg_expense

def recommend_saving_for_goal(user, goal, target_probability=DEFAULT_TARGET_PROB, today=None):
    """
    Main function to return an optimization recommendation.
    Returns a dict with:
      - remaining (float)
      - months_left (int)
      - mu (float), sigma (float), months_count (int)
      - required_monthly (float)  # naive required = remaining / months_left
      - recommended_extra (float) # extra monthly saving on top of mu to reach probability
      - new_monthly_target (float) # mu + recommended_extra
      - expense_reduction_pct (float) # approximate % reduction to meet target if needed
      - feasible (bool) and message/advice (string)
    """
    today = today or date.today()
    current = getattr(goal, "current_amount", Decimal("0"))
    if current is None:
        current = Decimal("0")

    remaining = float(max(Decimal("0"), goal.target_amount - current))
    
    months_left = months_between(today, goal.deadline) or 0

    # Basic checks
    if months_left <= 0:
        return {
            "remaining": remaining,
            "months_left": months_left,
            "feasible": False,
            "message": "Goal deadline has passed or is today."
        }

    mu, sigma, months_count, avg_income, avg_expense = compute_monthly_savings_stats(user)

    # Naive required monthly saving to meet goal deterministically
    required_monthly = remaining / months_left

    # Cold-start or insufficient history
    if months_count < MIN_MONTHS_FOR_STATS:
        # propose conservative template: use either last known savings or a fixed suggestion
        fallback_extra = max(0.0, required_monthly - mu)
        fallback_extra = max(fallback_extra, COLD_START_MONTHLY_SAVING - mu) if mu == 0 else fallback_extra
        new_monthly = mu + fallback_extra
        # compute approximate expense reduction relative to avg_income if available
        if avg_income > 0:
            needed_reduction = max(0.0, (new_monthly - mu) / avg_income)
        else:
            needed_reduction = None

        return {
            "remaining": remaining,
            "months_left": months_left,
            "mu": mu,
            "sigma": sigma,
            "months_count": months_count,
            "required_monthly": required_monthly,
            "recommended_extra": fallback_extra,
            "new_monthly_target": new_monthly,
            "expense_reduction_pct": needed_reduction,
            "feasible": True if new_monthly <= max(0.0, avg_income - avg_expense + mu) else False,
            "message": "Cold-start strategy used: not enough history. Follow conservative recommendation."
        }

    # Normal case: we have stats
    N = months_left
    mu0 = mu
    sigma0 = sigma

    if sigma0 <= 0:
        # deterministic case (no volatility)
        extra_needed = max(0.0, required_monthly - mu0)
        new_monthly = mu0 + extra_needed
    else:
        z = norm.ppf(1 - target_probability)  # negative for p>0.5
        numerator = remaining - N * mu0 - z * math.sqrt(N) * sigma0
        extra_needed = numerator / N
        extra_needed = max(0.0, extra_needed)  # no negative extra
        # add small safety buffer
        extra_needed = extra_needed * (1.0 + MIN_SAVING_BUFFER_PCT)
        new_monthly = mu0 + extra_needed

    # feasibility: can't recommend more than disposable income (avg_income - avg_expense) + mu
    disposable = max(0.0, avg_income - avg_expense)  # typical leftover if any
    feasible = True
    if new_monthly > (disposable + mu0 + 1e-6):
        feasible = False

    # approximate expense reduction percent to achieve extra_needed (relative to avg_income)
    expense_reduction_pct = None
    if avg_income > 0:
        expense_reduction_pct = min(1.0, max(0.0, extra_needed / avg_income))

    # human readable message
    if extra_needed <= 0:
        message = "Great — your historical savings are on track to meet the goal with the selected confidence."
    elif not feasible:
        message = ("To meet this goal you would need to increase monthly savings by {:.2f}. "
                   "That exceeds your typical disposable income. Consider extending the deadline or increasing income."
                  ).format(extra_needed)
    else:
        message = ("We recommend increasing monthly savings by {:.2f} ({:.1%} of your average income) "
                   "to have ~{:.0%} probability of success."
                  ).format(extra_needed, expense_reduction_pct or 0.0, target_probability)

    return {
        "remaining": remaining,
        "months_left": N,
        "mu": mu0,
        "sigma": sigma0,
        "months_count": months_count,
        "required_monthly": required_monthly,
        "recommended_extra": extra_needed,
        "new_monthly_target": new_monthly,
        "expense_reduction_pct": expense_reduction_pct,
        "disposable": disposable,
        "feasible": feasible,
        "message": message
    }
