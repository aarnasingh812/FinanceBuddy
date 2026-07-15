"""
Transaction anomaly detection.

Combines simple statistical/rule-based checks with an optional
Local Outlier Factor (LOF) pass to flag suspicious expense and income
transactions for a user.

Public API: detect_anomalies(user_id) -> dict
"""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, stdev
from typing import Callable

import numpy as np
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler, LabelEncoder

from finance.models import Transaction


# ---------------------------------------------------------------------------
# Rule-based constants
# ---------------------------------------------------------------------------
MIN_HISTORY_TXNS          = 5    # minimum expenses before any analysis
Z_SCORE_THRESHOLD         = 2.0  # standard deviations to flag
CATEGORY_SINGLE_TXN_RATIO = 0.5  # flag if single txn > 50% of monthly avg
REPEAT_WINDOW_DAYS        = 7    # sliding window for duplicate detection
REPEAT_MIN_COUNT          = 3    # flag if same (title, amount) >= 3 in window
DAILY_SPIKE_MULTIPLIER    = 3.0  # flag if txn > 3x average daily spend
MONTHLY_HISTORY_MIN       = 3    # prior months needed for monthly spike check
MONTHLY_HISTORY_MAX       = 5    # cap the rolling baseline window
MONTHLY_SPIKE_MULTIPLIER  = 2.0  # flag if current-month category total > 2x prior avg
INCOME_SPIKE_MULTIPLIER   = 2.0  # flag if single income txn > 2x prior monthly avg income

# ---------------------------------------------------------------------------
# LOF constants
# ---------------------------------------------------------------------------
ML_MIN_SAMPLES      = 30   # minimum total transactions to activate LOF
LOF_MIN_CAT_SAMPLES = 15   # minimum per-category samples to run per-category LOF;
                            # categories below this are pooled into a global pass
LOF_N_NEIGHBORS     = 10   # k for LOF; reduced to work on smaller personal datasets
LOF_CONTAMINATION   = 0.05 # expected fraction of outliers (5%)


# ===========================================================================
# Small shared helpers
# ===========================================================================

def _month_key(d: date) -> tuple:
    """(year, month) key used to bucket transactions by calendar month."""
    return (d.year, d.month)


def _shift_month_start(d: date, months: int) -> date:
    """First day of the month that is `months` away from d's month.

    `months` may be negative (go back in time) or positive (go forward).
    """
    absolute_month = d.year * 12 + (d.month - 1) + months
    year, month = divmod(absolute_month, 12)
    return date(year, month + 1, 1)


def _ratio_signal(ratio: float, threshold: float, score_scale: float,
                   build_detail: Callable[[], str]):
    """Shared "is this ratio over the threshold" check used by several signals.

    Returns (triggered, score, detail) exactly like the individual signal
    functions did before refactoring.
    """
    if ratio <= threshold:
        return False, 0.0, ""
    score = min(1.0, ratio / score_scale)
    return True, round(score, 2), build_detail()


def _recent_month_baseline(monthly_totals: dict, before_month_key: tuple):
    """Average of the most recent prior months, capped at MONTHLY_HISTORY_MAX.

    Returns (baseline_avg, months_used) or (None, 0) if there isn't enough
    history (MONTHLY_HISTORY_MIN prior months) to compute one.
    """
    prior_months = sorted(
        (ym, total) for ym, total in monthly_totals.items() if ym < before_month_key
    )
    prior_months.reverse()  # most recent first

    if len(prior_months) < MONTHLY_HISTORY_MIN:
        return None, 0

    baseline_months = prior_months[:MONTHLY_HISTORY_MAX]
    baseline_avg = mean(total for _, total in baseline_months)
    return baseline_avg, len(baseline_months)


# ===========================================================================
# Feature engineering
# ===========================================================================

def _build_feature_matrix(transactions):
    """Turn raw transactions into a numeric feature matrix for LOF.

    Features per transaction: amount, weekday, day-of-month, encoded
    category, days since previous transaction, amount-vs-category-average
    ratio, and running monthly total for that transaction's category month.
    """
    if not transactions:
        return None, None, []

    txns = sorted(transactions, key=lambda t: t["date"])

    # Per-category mean for the ratio feature (computed over the full set)
    cat_buckets = defaultdict(list)
    for t in txns:
        cat_buckets[t["category"]].append(float(t["amount"]))
    cat_mean = {cat: mean(amounts) for cat, amounts in cat_buckets.items()}

    cat_encoder = LabelEncoder()
    cat_encoder.fit([t["category"] for t in txns])

    monthly_cumulative = defaultdict(float)
    rows, txn_ids = [], []
    prev_date = None

    for t in txns:
        amt = float(t["amount"])
        txn_date = t["date"]
        cat = t["category"]
        month_key = _month_key(txn_date)

        days_gap = (txn_date - prev_date).days if prev_date else 0
        prev_date = txn_date

        cat_avg = cat_mean.get(cat, amt)
        ratio = amt / cat_avg if cat_avg > 0 else 1.0

        monthly_cumulative[month_key] += amt

        rows.append([
            amt,
            txn_date.weekday(),
            txn_date.day,
            int(cat_encoder.transform([cat])[0]),
            days_gap,
            ratio,
            monthly_cumulative[month_key],
        ])
        txn_ids.append(t["id"])

    return np.array(rows, dtype=float), cat_encoder, txn_ids


# ===========================================================================
# LOF signal
# ===========================================================================

def _lof_signals(transactions):
    """Run Local Outlier Factor over expense transactions, per category
    where there's enough data, and pooled globally otherwise.
    """
    if not transactions or len(transactions) < ML_MIN_SAMPLES:
        return {}

    cat_groups = defaultdict(list)
    for t in transactions:
        cat_groups[t["category"]].append(t)

    results = {}
    leftover = []
    for cat, cat_txns in cat_groups.items():
        if len(cat_txns) >= LOF_MIN_CAT_SAMPLES:
            results.update(_run_lof(cat_txns, scope=f"within your '{cat}' transactions"))
        else:
            leftover.extend(cat_txns)

    # Global pass for categories that didn't have enough data on their own
    if len(leftover) >= ML_MIN_SAMPLES:
        results.update(_run_lof(leftover, scope="across your transaction history"))

    return results


def _run_lof(txn_subset, scope: str):
    """Fit LOF on a subset of transactions and return {txn_id: (score, detail)}
    for the ones flagged as outliers.
    """
    X, _, txn_ids = _build_feature_matrix(txn_subset)
    if X is None:
        return {}

    # n_neighbors must be < n_samples
    n_neighbors = min(LOF_N_NEIGHBORS, len(X) - 1)
    if n_neighbors < 2:
        return {}

    X_scaled = StandardScaler().fit_transform(X)

    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=LOF_CONTAMINATION)
    labels = lof.fit_predict(X_scaled)  # 1 = inlier, -1 = outlier

    # negative_outlier_factor_ is negative LOF score; flip so higher = more anomalous
    raw_scores = -lof.negative_outlier_factor_
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s == min_s:
        norm_scores = np.zeros_like(raw_scores)
    else:
        norm_scores = (raw_scores - min_s) / (max_s - min_s)

    flagged = {}
    for i, txn_id in enumerate(txn_ids):
        if labels[i] != -1:
            continue
        score = round(float(norm_scores[i]), 2)
        detail = (
            f"LOF detected this as a local density outlier {scope} "
            f"(anomaly score {score:.2f}/1.00). Its combination of amount, "
            f"timing, and spending pattern is unlike nearby transactions."
        )
        flagged[txn_id] = (score, detail)

    return flagged


# ===========================================================================
# Rule-based helpers
# ===========================================================================

def _build_category_stats(expenses):
    """Return (cat_amounts, cat_monthly):
    - cat_amounts: {category: [amount, ...]}
    - cat_monthly: {category: {(year, month): total_amount}}
    """
    cat_amounts = defaultdict(list)
    cat_monthly = defaultdict(lambda: defaultdict(float))
    for txn in expenses:
        cat = txn["category"]
        amt = float(txn["amount"])
        cat_amounts[cat].append(amt)
        cat_monthly[cat][_month_key(txn["date"])] += amt
    return cat_amounts, cat_monthly


def _build_income_monthly_stats(income_txns):
    """Return (monthly_income, income_amounts):
    - monthly_income: {(year, month): total_amount}
    - income_amounts: flat list of all income amounts
    """
    monthly_income = defaultdict(float)
    income_amounts = []
    for txn in income_txns:
        amt = float(txn["amount"])
        monthly_income[_month_key(txn["date"])] += amt
        income_amounts.append(amt)
    return monthly_income, income_amounts


def _z_score_signal(amount, cat_amounts_list):
    """Flag if `amount` is an outlier (> Z_SCORE_THRESHOLD std devs above
    the mean) within its category's transaction history.
    """
    if len(cat_amounts_list) < MIN_HISTORY_TXNS or len(cat_amounts_list) < 2:
        return False, 0.0, ""

    mu = mean(cat_amounts_list)
    sd = stdev(cat_amounts_list)
    if sd == 0:
        return False, 0.0, ""

    z = (amount - mu) / sd
    if z <= Z_SCORE_THRESHOLD:
        return False, 0.0, ""

    score = min(1.0, z / 4.0)
    detail = (
        f"Amount {amount:.2f} has a Z-score of {z:.2f} in its category "
        f"(mean {mu:.2f}, std {sd:.2f}). Threshold is {Z_SCORE_THRESHOLD}."
    )
    return True, round(score, 2), detail


def _category_spike_signal(amount, category, txn_date, cat_monthly):
    """Flag if a single transaction is a large chunk (> CATEGORY_SINGLE_TXN_RATIO)
    of its category's average monthly spend.
    """
    monthly_totals = cat_monthly.get(category, {})
    txn_month_key = _month_key(txn_date)

    prior_months = sorted(
        [ym for ym in monthly_totals.keys() if ym < txn_month_key],
        reverse=True
    )
    if len(prior_months) > 12:
        prior_months = prior_months[:12]

    if len(prior_months) < 2:
        return False, 0.0, ""

    avg_monthly = mean(monthly_totals[ym] for ym in prior_months)
    if avg_monthly == 0:
        return False, 0.0, ""

    ratio = amount / avg_monthly
    return _ratio_signal(
        ratio, CATEGORY_SINGLE_TXN_RATIO, score_scale=2.0,
        build_detail=lambda: (
            f"Single transaction of {amount:.2f} is {ratio:.0%} of the "
            f"average monthly spend ({avg_monthly:.2f}) in '{category}'."
        ),
    )


def _daily_spike_signal(amount, daily_avg):
    """Flag if a transaction is far above the user's average daily spend."""
    if daily_avg == 0:
        return False, 0.0, ""

    ratio = amount / daily_avg
    return _ratio_signal(
        ratio, DAILY_SPIKE_MULTIPLIER, score_scale=10.0,
        build_detail=lambda: (
            f"Amount {amount:.2f} is {ratio:.1f}x the average daily "
            f"expense ({daily_avg:.2f}). Threshold is {DAILY_SPIKE_MULTIPLIER}x."
        ),
    )


def _category_monthly_spike_signal(category, current_month_key, cat_monthly):
    """Flag if a category's total for the current month is far above its
    recent-month baseline.
    """
    monthly_totals = cat_monthly.get(category, {})
    baseline_avg, months_used = _recent_month_baseline(monthly_totals, current_month_key)
    if baseline_avg is None or baseline_avg == 0:
        return False, 0.0, ""

    current_total = monthly_totals.get(current_month_key, 0.0)
    if current_total == 0:
        return False, 0.0, ""

    ratio = current_total / baseline_avg
    return _ratio_signal(
        ratio, MONTHLY_SPIKE_MULTIPLIER, score_scale=MONTHLY_SPIKE_MULTIPLIER * 2,
        build_detail=lambda: (
            f"Category '{category}' total this month ({current_total:.2f}) is "
            f"{ratio:.1f}x the average of the prior {months_used} months "
            f"({baseline_avg:.2f}). Threshold is {MONTHLY_SPIKE_MULTIPLIER}x."
        ),
    )


def _income_spike_signal(amount, txn_date, monthly_income):
    """Flag if a single income transaction is far above the recent monthly
    income baseline.
    """
    current_month_key = _month_key(txn_date)
    baseline_avg, months_used = _recent_month_baseline(monthly_income, current_month_key)
    if baseline_avg is None or baseline_avg == 0:
        return False, 0.0, ""

    ratio = amount / baseline_avg
    return _ratio_signal(
        ratio, INCOME_SPIKE_MULTIPLIER, score_scale=INCOME_SPIKE_MULTIPLIER * 2,
        build_detail=lambda: (
            f"Income of {amount:.2f} is {ratio:.1f}x the average monthly "
            f"income of the prior {months_used} months ({baseline_avg:.2f}). "
            f"Threshold is {INCOME_SPIKE_MULTIPLIER}x."
        ),
    )


def _find_suspicious_repeats(expenses_in_window):
    """Flag transactions that repeat the same (title, amount) at least
    REPEAT_MIN_COUNT times within a REPEAT_WINDOW_DAYS sliding window.

    Returns {txn_id: (repeat_count, score, detail)}.
    """
    groups = defaultdict(list)
    for txn in expenses_in_window:
        key = (txn["title"].strip().lower(), float(txn["amount"]))
        groups[key].append(txn)

    flagged = {}
    for (title, amount), txns in groups.items():
        txns_sorted = sorted(txns, key=lambda t: t["date"])
        for i, anchor in enumerate(txns_sorted):
            window_end = anchor["date"] + timedelta(days=REPEAT_WINDOW_DAYS)
            cluster = [t for t in txns_sorted[i:] if t["date"] <= window_end]
            if len(cluster) < REPEAT_MIN_COUNT:
                continue

            score = min(1.0, len(cluster) / 5.0)
            detail = (
                f"'{title}' for {amount:.2f} appeared {len(cluster)} "
                f"times within {REPEAT_WINDOW_DAYS} days."
            )
            for t in cluster:
                if t["id"] not in flagged or flagged[t["id"]][1] < score:
                    flagged[t["id"]] = (len(cluster), round(score, 2), detail)

    return flagged


# ===========================================================================
# Window analysis (expense / income)
# ===========================================================================

def _analyse_expense_window(window_txns, window_month_key, cat_amounts, cat_monthly,
                             daily_avg, lof_results):
    """Run every expense signal over a window of transactions and return the
    flagged anomalies sorted by score (highest first), or None if empty.
    """
    if not window_txns:
        return None

    repeat_flags = _find_suspicious_repeats(window_txns)

    # Category monthly spike is the same for every txn in a category for this
    # window's month, so compute it once per category instead of per txn.
    monthly_spike_by_cat = {
        cat: _category_monthly_spike_signal(cat, window_month_key, cat_monthly)
        for cat in {t["category"] for t in window_txns}
    }

    anomalies = []
    for txn in window_txns:
        amt = float(txn["amount"])
        txn_id = txn["id"]
        reasons = []

        def add_reason(signal_name, trig, score, detail):
            if trig:
                reasons.append({"signal": signal_name, "detail": detail, "score": score})

        add_reason("amount_outlier", *_z_score_signal(amt, cat_amounts.get(txn["category"], [])))
        add_reason("category_spike", *_category_spike_signal(amt, txn["category"], txn["date"], cat_monthly))

        if txn_id in repeat_flags:
            _, score, detail = repeat_flags[txn_id]
            reasons.append({"signal": "suspicious_repeat", "detail": detail, "score": score})

        add_reason("daily_spike", *_daily_spike_signal(amt, daily_avg))
        add_reason("category_monthly_spike", *monthly_spike_by_cat.get(txn["category"], (False, 0.0, "")))

        if txn_id in lof_results:
            score, detail = lof_results[txn_id]
            reasons.append({"signal": "lof", "detail": detail, "score": score})

        if reasons:
            anomalies.append({
                "transaction_id": txn_id,
                "title": txn["title"],
                "amount": amt,
                "date": txn["date"].isoformat(),
                "category": txn["category"],
                "anomaly_score": max(r["score"] for r in reasons),
                "anomaly_reasons": reasons,
                # True if LOF spotted something the rules alone missed
                "ml_contributed": any(r["signal"] == "lof" for r in reasons),
            })

    if not anomalies:
        return None
    anomalies.sort(key=lambda a: a["anomaly_score"], reverse=True)
    return anomalies


def _analyse_income_window(income_window_txns, monthly_income):
    """Rule-based only (income is typically sparse) — flags income spikes."""
    if not income_window_txns:
        return None

    anomalies = []
    for txn in income_window_txns:
        amt = float(txn["amount"])
        trig, score, detail = _income_spike_signal(amt, txn["date"], monthly_income)
        if not trig:
            continue
        anomalies.append({
            "transaction_id": txn["id"],
            "title": txn["title"],
            "amount": amt,
            "date": txn["date"].isoformat(),
            "category": txn["category"],
            "anomaly_score": score,
            "anomaly_reasons": [{"signal": "income_spike", "detail": detail, "score": score}],
            "ml_contributed": False,
        })

    if not anomalies:
        return None
    anomalies.sort(key=lambda a: a["anomaly_score"], reverse=True)
    return anomalies


# ===========================================================================
# Main detection function
# ===========================================================================

def detect_anomalies(user_id: int) -> dict:
    today = date.today()
    current_month_start = today.replace(day=1)
    current_month_key = _month_key(today)
    three_months_ago = _shift_month_start(current_month_start, -3)
    one_month_ago_key = _month_key(_shift_month_start(current_month_start, -1))

    # ------------------------------------------------------------------
    # Fetch all transactions
    # ------------------------------------------------------------------
    all_expenses = list(
        Transaction.objects
        .filter(user_id=user_id, transaction_type="Expense")
        .order_by("date")
        .values("id", "title", "amount", "date", "category")
    )
    all_income = list(
        Transaction.objects
        .filter(user_id=user_id, transaction_type="Income")
        .order_by("date")
        .values("id", "title", "amount", "date", "category")
    )

    if len(all_expenses) < MIN_HISTORY_TXNS:
        return {
            "current_month": None,
            "last_3_months": None,
            "current_month_income_anomalies": None,
            "last_3_months_income_anomalies": None,
            "ml_active": False,
            "insufficient_data": True,
        }

    # ------------------------------------------------------------------
    # Rule-based: global stats
    # ------------------------------------------------------------------
    cat_amounts, cat_monthly = _build_category_stats(all_expenses)
    monthly_income, _ = _build_income_monthly_stats(all_income)

    start_date = date(today.year - 1, today.month, 1)
    has_older_data = len(all_expenses) > 0 and all_expenses[0]["date"] < start_date

    if has_older_data:
        daily_avg_expenses = [
            t for t in all_expenses if start_date <= t["date"] < current_month_start
        ]
    else:
        daily_avg_expenses = [
            t for t in all_expenses if t["date"] < current_month_start
        ]

    if daily_avg_expenses:
        date_range = (daily_avg_expenses[-1]["date"] - daily_avg_expenses[0]["date"]).days + 1
        total_spent = sum(float(t["amount"]) for t in daily_avg_expenses)
        daily_avg = total_spent / max(date_range, 1)
    else:
        daily_avg = 0.0

    # ------------------------------------------------------------------
    # LOF: train on full expense history.
    # Active only when user has >= ML_MIN_SAMPLES transactions.
    # ------------------------------------------------------------------
    ml_active = len(all_expenses) >= ML_MIN_SAMPLES
    lof_results = _lof_signals(all_expenses) if ml_active else {}

    # ------------------------------------------------------------------
    # Window splits
    # ------------------------------------------------------------------
    current_month_txns = [t for t in all_expenses if t["date"] >= current_month_start]
    last_3_months_txns = [
        t for t in all_expenses if three_months_ago <= t["date"] < current_month_start
    ]
    current_month_income = [t for t in all_income if t["date"] >= current_month_start]
    last_3_months_income = [
        t for t in all_income if three_months_ago <= t["date"] < current_month_start
    ]

    # ------------------------------------------------------------------
    # Analyse each window and return
    # ------------------------------------------------------------------
    return {
        "current_month": _analyse_expense_window(
            current_month_txns, current_month_key, cat_amounts, cat_monthly, daily_avg, lof_results
        ),
        "last_3_months": _analyse_expense_window(
            last_3_months_txns, one_month_ago_key, cat_amounts, cat_monthly, daily_avg, lof_results
        ),
        "current_month_income_anomalies": _analyse_income_window(current_month_income, monthly_income),
        "last_3_months_income_anomalies": _analyse_income_window(last_3_months_income, monthly_income),
        # Metadata — useful for the UI
        "ml_active": ml_active,
        "ml_min_samples_required": ML_MIN_SAMPLES,
        "user_total_expenses": len(all_expenses),
    }