"""
Recurring Transaction Detection Engine

Clusters transactions by (normalized_title, amount), scores each cluster
on interval regularity using coefficient of variation, and classifies
recurring clusters into three fixed interval buckets: 15_days, 30_days, 90_days.

Returns null per bucket when insufficient data exists (e.g. new users).
"""

import re
from collections import defaultdict
from statistics import mean, stdev
from datetime import timedelta

from finance.models import Transaction


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_OCCURRENCES = 3          # minimum transactions in a cluster to evaluate
CV_THRESHOLD = 0.15          # max coefficient of variation (15 %)

# Bucket definitions: (bucket_key, label, min_gap, max_gap)
INTERVAL_BUCKETS = [
    ("15_days", "15 Days", 10, 22),
    ("30_days", "30 Days", 23, 60),
    ("90_days", "90 Days", 61, 120),
]

# Keyword → recurring type mapping
TYPE_KEYWORDS = {
    "Salary":           ["salary", "payroll", "stipend", "wages"],
    "Rent":             ["rent", "lease", "housing"],
    "Subscription":     ["netflix", "spotify", "subscription", "prime",
                         "hulu", "disney", "youtube", "hotstar", "zee5",
                         "jio", "airtel", "membership"],
    "EMI":              ["emi", "loan", "mortgage", "installment"],
    "Bill":             ["electric", "water", "gas", "internet", "phone",
                         "bill", "utility", "broadband", "wifi", "recharge"],
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _normalize_title(title: str) -> str:
    """Lowercase, strip, and collapse whitespace."""
    return re.sub(r"\s+", " ", title.strip().lower())


def _classify_type(title: str) -> str:
    """Infer recurring type from title keywords."""
    lower = title.lower()
    for rtype, keywords in TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return rtype
    return "Regular Transfer"


def _bucket_for_gap(mean_gap: float):
    """Return the bucket key that this mean_gap falls into, or None."""
    for key, _label, lo, hi in INTERVAL_BUCKETS:
        if lo <= mean_gap <= hi:
            return key
    return None


def _gap_stats(dates):
    """Return (mean_gap, coefficient_of_variation) for a sorted list of dates,
    or None if there's no usable gap (single date, or all gaps are zero).
    """
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    if not gaps:
        return None

    mean_gap = mean(gaps)
    if mean_gap == 0:
        return None  # all on the same day — not recurring

    std_gap = stdev(gaps) if len(gaps) >= 2 else 0.0
    return mean_gap, std_gap / mean_gap


def _build_pattern(amount, txns_sorted, mean_gap, cv):
    """Build the recurring-pattern dict for a cluster that passed all checks."""
    last_date = txns_sorted[-1]["date"]
    next_expected = last_date + timedelta(days=round(mean_gap))
    original_title = txns_sorted[-1]["title"]  # use most recent title casing

    return {
        "title": original_title,
        "amount": amount,
        "mean_gap_days": round(mean_gap, 1),
        "confidence": round(max(0.0, min(1.0, 1.0 - cv)), 2),
        "next_expected_date": next_expected.isoformat(),
        "recurring_type": _classify_type(original_title),
        "occurrences": len(txns_sorted),
        "last_date": last_date.isoformat(),
        "transaction_ids": [t["id"] for t in txns_sorted],
    }


def _evaluate_cluster(amount, txns):
    """Check whether a (title, amount) cluster looks recurring.

    Returns (bucket_key, pattern_dict) if it qualifies, otherwise None.
    """
    if len(txns) < MIN_OCCURRENCES:
        return None  # not enough data points

    txns_sorted = sorted(txns, key=lambda t: t["date"])
    dates = [t["date"] for t in txns_sorted]

    gap_stats = _gap_stats(dates)
    if gap_stats is None:
        return None
    mean_gap, cv = gap_stats

    if cv > CV_THRESHOLD:
        return None  # too irregular

    bucket_key = _bucket_for_gap(mean_gap)
    if bucket_key is None:
        return None  # outside all defined ranges

    return bucket_key, _build_pattern(amount, txns_sorted, mean_gap, cv)


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def detect_recurring_transactions(user_id: int) -> dict:
    """
    Analyse all transactions for the given user and return detected
    recurring patterns grouped into three fixed interval buckets.

    Returns
    -------
    dict with keys "15_days", "30_days", "90_days".
    Each value is either a list of recurring-pattern dicts or None.
    """

    # 1. Fetch all transactions for this user, ordered by date
    transactions = (
        Transaction.objects
        .filter(user_id=user_id)
        .order_by("date")
        .values("id", "title", "amount", "date")
    )

    # 2. Cluster by (normalized_title, amount)
    clusters = defaultdict(list)
    for txn in transactions:
        key = (_normalize_title(txn["title"]), float(txn["amount"]))
        clusters[key].append(txn)

    # 3. Evaluate each cluster
    detected = []  # list of (bucket_key, pattern_dict)
    for (norm_title, amount), txns in clusters.items():
        evaluation = _evaluate_cluster(amount, txns)
        if evaluation is not None:
            detected.append(evaluation)

    # 4. Group into the three fixed buckets, sorted by confidence within each
    result = {}
    for key, _label, _lo, _hi in INTERVAL_BUCKETS:
        bucket_items = [pattern for bk, pattern in detected if bk == key]
        bucket_items.sort(key=lambda p: p["confidence"], reverse=True)
        result[key] = bucket_items if bucket_items else None

    return result