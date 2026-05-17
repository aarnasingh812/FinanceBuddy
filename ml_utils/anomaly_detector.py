"""
Anomaly Detection Engine

Analyses a user's expense transactions and flags anomalous ones using
four independent statistical signals:

1. Amount Z-Score Outlier      – per-category amount deviations
2. Category Monthly Spending   – single txn vs. historical monthly avg
3. Suspicious Repeats          – same (title, amount) clusters in 7 days
4. Daily Spike                 – single txn vs. average daily expense

Results are split into two windows: current_month and last_3_months.
Returns None per window when no anomalies are detected.
"""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, stdev

from finance.models import Transaction

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_HISTORY_TXNS = 5            # need at least this many expenses to analyse
Z_SCORE_THRESHOLD = 2.0         # flag if z > 2.0
CATEGORY_SINGLE_TXN_RATIO = 0.5 # flag if single txn > 50 % of monthly avg
REPEAT_WINDOW_DAYS = 7          # sliding window for duplicate detection
REPEAT_MIN_COUNT = 3            # flag if same (title, amount) >= 3 in window
DAILY_SPIKE_MULTIPLIER = 3.0    # flag if txn > 3x average daily spend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_category_stats(expenses):
    """
    Return two dicts keyed by category:
      cat_amounts  : {category: [amount, ...]}  — all-time amounts
      cat_monthly  : {category: {(year, month): total, ...}}
    """
    cat_amounts = defaultdict(list)
    cat_monthly = defaultdict(lambda: defaultdict(float))

    for txn in expenses:
        cat = txn["category"]
        amt = float(txn["amount"])
        cat_amounts[cat].append(amt)
        cat_monthly[cat][(txn["date"].year, txn["date"].month)] += amt

    return cat_amounts, cat_monthly


def _z_score_signal(amount, cat_amounts_list):
    """Return (triggered: bool, score: float, detail: str)."""
    if len(cat_amounts_list) < MIN_HISTORY_TXNS:
        return False, 0.0, ""

    mu = mean(cat_amounts_list)
    if len(cat_amounts_list) < 2:
        return False, 0.0, ""
    sd = stdev(cat_amounts_list)
    if sd == 0:
        return False, 0.0, ""

    z = (amount - mu) / sd
    if z > Z_SCORE_THRESHOLD:
        score = min(1.0, z / 4.0)
        detail = (
            f"Amount {amount:.2f} has a Z-score of {z:.2f} in its category "
            f"(mean {mu:.2f}, std {sd:.2f}). Threshold is {Z_SCORE_THRESHOLD}."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _category_spike_signal(amount, category, txn_date, cat_monthly):
    """Flag if a single txn exceeds CATEGORY_SINGLE_TXN_RATIO of the
    user's average monthly spend in that category."""
    monthly_totals = cat_monthly.get(category, {})
    if len(monthly_totals) < 2:
        return False, 0.0, ""

    avg_monthly = mean(monthly_totals.values())
    if avg_monthly == 0:
        return False, 0.0, ""

    ratio = amount / avg_monthly
    if ratio > CATEGORY_SINGLE_TXN_RATIO:
        score = min(1.0, ratio / 2.0)
        detail = (
            f"Single transaction of {amount:.2f} is {ratio:.0%} of the "
            f"average monthly spend ({avg_monthly:.2f}) in '{category}'."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _daily_spike_signal(amount, daily_avg):
    """Flag if a single txn is > DAILY_SPIKE_MULTIPLIER × daily average."""
    if daily_avg == 0:
        return False, 0.0, ""

    ratio = amount / daily_avg
    if ratio > DAILY_SPIKE_MULTIPLIER:
        score = min(1.0, ratio / 10.0)
        detail = (
            f"Amount {amount:.2f} is {ratio:.1f}x the average daily "
            f"expense ({daily_avg:.2f}). Threshold is {DAILY_SPIKE_MULTIPLIER}x."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _find_suspicious_repeats(expenses_in_window):
    """
    Return a dict  {txn_id: (count, score, detail)}  for transactions
    whose (title, amount) appears >= REPEAT_MIN_COUNT within any
    REPEAT_WINDOW_DAYS sliding window.
    """
    # Group by (lowercase title, amount)
    groups = defaultdict(list)
    for txn in expenses_in_window:
        key = (txn["title"].strip().lower(), float(txn["amount"]))
        groups[key].append(txn)

    flagged = {}
    for (title, amount), txns in groups.items():
        txns_sorted = sorted(txns, key=lambda t: t["date"])
        # Sliding window check
        for i, anchor in enumerate(txns_sorted):
            window_end = anchor["date"] + timedelta(days=REPEAT_WINDOW_DAYS)
            cluster = [t for t in txns_sorted[i:] if t["date"] <= window_end]
            if len(cluster) >= REPEAT_MIN_COUNT:
                score = min(1.0, len(cluster) / 5.0)
                detail = (
                    f"'{title}' for {amount:.2f} appeared {len(cluster)} "
                    f"times within {REPEAT_WINDOW_DAYS} days."
                )
                for t in cluster:
                    # Keep the highest score if already flagged
                    if t["id"] not in flagged or flagged[t["id"]][1] < score:
                        flagged[t["id"]] = (len(cluster), round(score, 2), detail)
    return flagged


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def detect_anomalies(user_id: int) -> dict:
    """
    Analyse expense transactions for the given user and return detected
    anomalies split by time window.

    Returns
    -------
    dict with keys "current_month" and "last_3_months".
    Each value is a list of anomaly dicts sorted by score desc, or None.
    """

    today = date.today()
    current_month_start = today.replace(day=1)
    three_months_ago = (current_month_start - timedelta(days=1)).replace(day=1)
    three_months_ago = (three_months_ago - timedelta(days=1)).replace(day=1)
    three_months_ago = (three_months_ago - timedelta(days=1)).replace(day=1)
    # three_months_ago is now the 1st of the month that is 3 months before current

    # ------------------------------------------------------------------
    # Fetch ALL expenses for this user (needed for historical stats)
    # ------------------------------------------------------------------
    all_expenses = list(
        Transaction.objects
        .filter(user_id=user_id, transaction_type="Expense")
        .order_by("date")
        .values("id", "title", "amount", "date", "category")
    )

    if len(all_expenses) < MIN_HISTORY_TXNS:
        return {
            "current_month": None,
            "last_3_months": None,
            "insufficient_data": True,
        }

    # Build historical stats from ALL expenses
    cat_amounts, cat_monthly = _build_category_stats(all_expenses)

    # Daily average across all history
    if all_expenses:
        date_range = (all_expenses[-1]["date"] - all_expenses[0]["date"]).days + 1
        total_spent = sum(float(t["amount"]) for t in all_expenses)
        daily_avg = total_spent / max(date_range, 1)
    else:
        daily_avg = 0.0

    # ------------------------------------------------------------------
    # Split transactions into the two windows
    # ------------------------------------------------------------------
    current_month_txns = [
        t for t in all_expenses if t["date"] >= current_month_start
    ]
    last_3_months_txns = [
        t for t in all_expenses
        if three_months_ago <= t["date"] < current_month_start
    ]

    # ------------------------------------------------------------------
    # Run detection on each window
    # ------------------------------------------------------------------
    def _analyse_window(window_txns):
        if not window_txns:
            return None

        # Pre-compute suspicious repeats for this window
        repeat_flags = _find_suspicious_repeats(window_txns)

        anomalies = []

        for txn in window_txns:
            amt = float(txn["amount"])
            reasons = []

            # Signal 1 — Amount Z-Score
            triggered, score, detail = _z_score_signal(
                amt, cat_amounts.get(txn["category"], [])
            )
            if triggered:
                reasons.append({
                    "signal": "amount_outlier",
                    "detail": detail,
                    "score": score,
                })

            # Signal 2 — Category monthly spending deviation
            triggered, score, detail = _category_spike_signal(
                amt, txn["category"], txn["date"], cat_monthly
            )
            if triggered:
                reasons.append({
                    "signal": "category_spike",
                    "detail": detail,
                    "score": score,
                })

            # Signal 3 — Suspicious repeats
            if txn["id"] in repeat_flags:
                _count, score, detail = repeat_flags[txn["id"]]
                reasons.append({
                    "signal": "suspicious_repeat",
                    "detail": detail,
                    "score": score,
                })

            # Signal 4 — Daily spike
            triggered, score, detail = _daily_spike_signal(amt, daily_avg)
            if triggered:
                reasons.append({
                    "signal": "daily_spike",
                    "detail": detail,
                    "score": score,
                })

            if reasons:
                anomaly_score = max(r["score"] for r in reasons)
                anomalies.append({
                    "transaction_id": txn["id"],
                    "title": txn["title"],
                    "amount": amt,
                    "date": txn["date"].isoformat(),
                    "category": txn["category"],
                    "anomaly_score": anomaly_score,
                    "anomaly_reasons": reasons,
                })

        if not anomalies:
            return None

        # Sort by anomaly score descending
        anomalies.sort(key=lambda a: a["anomaly_score"], reverse=True)
        return anomalies

    return {
        "current_month": _analyse_window(current_month_txns),
        "last_3_months": _analyse_window(last_3_months_txns),
    }
