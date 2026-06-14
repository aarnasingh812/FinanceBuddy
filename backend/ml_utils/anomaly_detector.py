"""
anomaly_detector.py
====================
Hybrid financial anomaly detector combining:

  Rule-based signals  (always active, from 5+ transactions)
    1. Z-Score per category
    2. Category single-txn spike vs monthly avg
    3. Suspicious repeat detection (sliding window)
    4. Daily spend spike
    5. Category monthly total spike vs prior 3-5 months
    6. Income spike vs prior monthly income

  ML signal  (activates at ML_MIN_SAMPLES = 30 transactions)
    7. Local Outlier Factor (LOF)

"""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, stdev

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
ML_MIN_SAMPLES         = 30   # minimum total transactions to activate LOF
LOF_MIN_CAT_SAMPLES    = 15   # minimum per-category samples to run per-category LOF;
                               # categories below this are pooled into a global pass
LOF_N_NEIGHBORS        = 10   # k for LOF; reduced to work on smaller personal datasets
LOF_CONTAMINATION      = 0.05 # expected fraction of outliers (5%)


# ===========================================================================
# Feature engineering
# ===========================================================================

def _build_feature_matrix(transactions):
    """
    Convert a list of transaction dicts into a numpy feature matrix.

    Features (7 total):
        0  amount                   — raw transaction amount
        1  day_of_week              — 0=Mon … 6=Sun
        2  day_of_month             — 1-31
        3  category_encoded         — integer label for category string
        4  days_since_last_txn      — calendar days since the previous transaction
                                      (0 for the very first transaction)
        5  amount_vs_cat_mean_ratio — amount / mean(amount) for that category;
                                      normalises scale differences across categories
        6  monthly_spend_so_far     — cumulative spend in this calendar month up to
                                      and including this transaction

    Transactions are sorted by date before processing so that features 4 and 6
    are computed in chronological order.

    Returns
        X       : np.ndarray shape (n, 7), float64
        cat_le  : fitted LabelEncoder (category strings -> integers)
        txn_ids : list[int]  transaction IDs in the same row order as X
    """
    if not transactions:
        return None, None, []

    txns = sorted(transactions, key=lambda t: t["date"])

    # Per-category mean for the ratio feature (computed over the full set)
    cat_buckets = defaultdict(list)
    for t in txns:
        cat_buckets[t["category"]].append(float(t["amount"]))
    cat_mean = {cat: mean(amts) for cat, amts in cat_buckets.items()}

    cat_le = LabelEncoder()
    cat_le.fit([t["category"] for t in txns])

    monthly_cumulative = defaultdict(float)
    rows      = []
    txn_ids   = []
    prev_date = None

    for t in txns:
        amt       = float(t["amount"])
        txn_date  = t["date"]
        month_key = (txn_date.year, txn_date.month)
        cat       = t["category"]

        days_gap  = (txn_date - prev_date).days if prev_date else 0
        prev_date = txn_date

        cat_avg = cat_mean.get(cat, amt)
        ratio   = amt / cat_avg if cat_avg > 0 else 1.0

        monthly_cumulative[month_key] += amt

        rows.append([
            amt,
            txn_date.weekday(),
            txn_date.day,
            int(cat_le.transform([cat])[0]),
            days_gap,
            ratio,
            monthly_cumulative[month_key],
        ])
        txn_ids.append(t["id"])

    return np.array(rows, dtype=float), cat_le, txn_ids


# ===========================================================================
# LOF signal
# ===========================================================================

def _lof_signals(transactions):
    """
    Run Local Outlier Factor over all expense transactions.

    Strategy
    --------
    For each category with >= LOF_MIN_CAT_SAMPLES transactions, run LOF
    independently within that category. This gives finer sensitivity — a
    ₹15,000 restaurant charge is judged against your restaurant history only,
    not your rent or grocery spend.

    Transactions in categories with fewer samples are pooled together and run
    through a single global LOF pass, which still provides multi-feature
    outlier detection without the per-category noise.

    Returns
    -------
    dict: { txn_id -> (score: float, detail: str) }
        Only transactions flagged as outliers (LOF label == -1) are included.
        score is normalised to [0, 1] where 1 = most anomalous.
    """
    if not transactions or len(transactions) < ML_MIN_SAMPLES:
        return {}

    results    = {}
    cat_groups = defaultdict(list)
    for t in transactions:
        cat_groups[t["category"]].append(t)

    leftover = []
    for cat, cat_txns in cat_groups.items():
        if len(cat_txns) >= LOF_MIN_CAT_SAMPLES:
            flagged = _run_lof(cat_txns, scope=f"within your '{cat}' transactions")
            results.update(flagged)
        else:
            leftover.extend(cat_txns)

    # Global pass for categories that didn't have enough data on their own
    if len(leftover) >= ML_MIN_SAMPLES:
        flagged = _run_lof(leftover, scope="across your transaction history")
        results.update(flagged)

    return results


def _run_lof(txn_subset, scope: str):
    """
    Fit LOF on a transaction subset and return flagged outliers.

    Parameters
    ----------
    txn_subset : list of transaction dicts
    scope      : human-readable string used in the detail message

    Returns
    -------
    dict: { txn_id -> (score: float, detail: str) }
    """
    X, _, txn_ids = _build_feature_matrix(txn_subset)
    if X is None:
        return {}

    # n_neighbors must be < n_samples
    n_neighbors = min(LOF_N_NEIGHBORS, len(X) - 1)
    if n_neighbors < 2:
        return {}

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    lof    = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=LOF_CONTAMINATION)
    labels = lof.fit_predict(X_scaled)  # 1 = inlier, -1 = outlier

    # negative_outlier_factor_ is negative LOF score; flip so higher = more anomalous
    raw_scores   = -lof.negative_outlier_factor_
    min_s, max_s = raw_scores.min(), raw_scores.max()
    norm_scores  = (
        np.zeros_like(raw_scores) if max_s == min_s
        else (raw_scores - min_s) / (max_s - min_s)
    )

    flagged = {}
    for i, txn_id in enumerate(txn_ids):
        if labels[i] != -1:
            continue
        score  = round(float(norm_scores[i]), 2)
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
    cat_amounts = defaultdict(list)
    cat_monthly = defaultdict(lambda: defaultdict(float))
    for txn in expenses:
        cat = txn["category"]
        amt = float(txn["amount"])
        cat_amounts[cat].append(amt)
        cat_monthly[cat][(txn["date"].year, txn["date"].month)] += amt
    return cat_amounts, cat_monthly


def _build_income_monthly_stats(income_txns):
    monthly_income = defaultdict(float)
    income_amounts = []
    for txn in income_txns:
        amt = float(txn["amount"])
        monthly_income[(txn["date"].year, txn["date"].month)] += amt
        income_amounts.append(amt)
    return monthly_income, income_amounts


def _z_score_signal(amount, cat_amounts_list):
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
        score  = min(1.0, z / 4.0)
        detail = (
            f"Amount {amount:.2f} has a Z-score of {z:.2f} in its category "
            f"(mean {mu:.2f}, std {sd:.2f}). Threshold is {Z_SCORE_THRESHOLD}."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _category_spike_signal(amount, category, txn_date, cat_monthly):
    monthly_totals = cat_monthly.get(category, {})
    if len(monthly_totals) < 2:
        return False, 0.0, ""
    avg_monthly = mean(monthly_totals.values())
    if avg_monthly == 0:
        return False, 0.0, ""
    ratio = amount / avg_monthly
    if ratio > CATEGORY_SINGLE_TXN_RATIO:
        score  = min(1.0, ratio / 2.0)
        detail = (
            f"Single transaction of {amount:.2f} is {ratio:.0%} of the "
            f"average monthly spend ({avg_monthly:.2f}) in '{category}'."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _daily_spike_signal(amount, daily_avg):
    if daily_avg == 0:
        return False, 0.0, ""
    ratio = amount / daily_avg
    if ratio > DAILY_SPIKE_MULTIPLIER:
        score  = min(1.0, ratio / 10.0)
        detail = (
            f"Amount {amount:.2f} is {ratio:.1f}x the average daily "
            f"expense ({daily_avg:.2f}). Threshold is {DAILY_SPIKE_MULTIPLIER}x."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _category_monthly_spike_signal(category, current_month_key, cat_monthly):
    monthly_totals = cat_monthly.get(category, {})
    prior_months   = sorted(
        [(ym, tot) for ym, tot in monthly_totals.items() if ym < current_month_key],
        key=lambda x: x[0], reverse=True,
    )
    if len(prior_months) < MONTHLY_HISTORY_MIN:
        return False, 0.0, ""
    baseline_months = prior_months[:MONTHLY_HISTORY_MAX]
    baseline_avg    = mean(t for _, t in baseline_months)
    if baseline_avg == 0:
        return False, 0.0, ""
    current_total = monthly_totals.get(current_month_key, 0.0)
    if current_total == 0:
        return False, 0.0, ""
    ratio = current_total / baseline_avg
    if ratio > MONTHLY_SPIKE_MULTIPLIER:
        score  = min(1.0, ratio / (MONTHLY_SPIKE_MULTIPLIER * 2))
        detail = (
            f"Category '{category}' total this month ({current_total:.2f}) is "
            f"{ratio:.1f}x the average of the prior {len(baseline_months)} months "
            f"({baseline_avg:.2f}). Threshold is {MONTHLY_SPIKE_MULTIPLIER}x."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _income_spike_signal(amount, txn_date, monthly_income):
    current_month_key = (txn_date.year, txn_date.month)
    prior_months      = sorted(
        [(ym, tot) for ym, tot in monthly_income.items() if ym < current_month_key],
        key=lambda x: x[0], reverse=True,
    )
    if len(prior_months) < MONTHLY_HISTORY_MIN:
        return False, 0.0, ""
    baseline_months = prior_months[:MONTHLY_HISTORY_MAX]
    baseline_avg    = mean(t for _, t in baseline_months)
    if baseline_avg == 0:
        return False, 0.0, ""
    ratio = amount / baseline_avg
    if ratio > INCOME_SPIKE_MULTIPLIER:
        score  = min(1.0, ratio / (INCOME_SPIKE_MULTIPLIER * 2))
        detail = (
            f"Income of {amount:.2f} is {ratio:.1f}x the average monthly "
            f"income of the prior {len(baseline_months)} months ({baseline_avg:.2f}). "
            f"Threshold is {INCOME_SPIKE_MULTIPLIER}x."
        )
        return True, round(score, 2), detail
    return False, 0.0, ""


def _find_suspicious_repeats(expenses_in_window):
    groups = defaultdict(list)
    for txn in expenses_in_window:
        key = (txn["title"].strip().lower(), float(txn["amount"]))
        groups[key].append(txn)

    flagged = {}
    for (title, amount), txns in groups.items():
        txns_sorted = sorted(txns, key=lambda t: t["date"])
        for i, anchor in enumerate(txns_sorted):
            window_end = anchor["date"] + timedelta(days=REPEAT_WINDOW_DAYS)
            cluster    = [t for t in txns_sorted[i:] if t["date"] <= window_end]
            if len(cluster) >= REPEAT_MIN_COUNT:
                score  = min(1.0, len(cluster) / 5.0)
                detail = (
                    f"'{title}' for {amount:.2f} appeared {len(cluster)} "
                    f"times within {REPEAT_WINDOW_DAYS} days."
                )
                for t in cluster:
                    if t["id"] not in flagged or flagged[t["id"]][1] < score:
                        flagged[t["id"]] = (len(cluster), round(score, 2), detail)
    return flagged


# ===========================================================================
# Main detection function
# ===========================================================================

def detect_anomalies(user_id: int) -> dict:

    today               = date.today()
    current_month_start = today.replace(day=1)
    current_month_key   = (today.year, today.month)

    three_months_ago = (current_month_start - timedelta(days=1)).replace(day=1)
    three_months_ago = (three_months_ago    - timedelta(days=1)).replace(day=1)
    three_months_ago = (three_months_ago    - timedelta(days=1)).replace(day=1)

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
            "current_month":                  None,
            "last_3_months":                  None,
            "current_month_income_anomalies": None,
            "last_3_months_income_anomalies": None,
            "ml_active":                      False,
            "insufficient_data":              True,
        }

    # ------------------------------------------------------------------
    # Rule-based: global stats
    # ------------------------------------------------------------------
    cat_amounts, cat_monthly = _build_category_stats(all_expenses)
    monthly_income, _        = _build_income_monthly_stats(all_income)

    date_range  = (all_expenses[-1]["date"] - all_expenses[0]["date"]).days + 1
    total_spent = sum(float(t["amount"]) for t in all_expenses)
    daily_avg   = total_spent / max(date_range, 1)

    # ------------------------------------------------------------------
    # LOF: train on full expense history
    # Active only when user has >= ML_MIN_SAMPLES transactions
    # ------------------------------------------------------------------
    ml_active   = len(all_expenses) >= ML_MIN_SAMPLES
    lof_results = _lof_signals(all_expenses) if ml_active else {}

    # ------------------------------------------------------------------
    # Window splits
    # ------------------------------------------------------------------
    current_month_txns   = [t for t in all_expenses if t["date"] >= current_month_start]
    last_3_months_txns   = [t for t in all_expenses
                             if three_months_ago <= t["date"] < current_month_start]
    current_month_income = [t for t in all_income if t["date"] >= current_month_start]
    last_3_months_income = [t for t in all_income
                             if three_months_ago <= t["date"] < current_month_start]

    one_month_ago    = (current_month_start - timedelta(days=1)).replace(day=1)
    last_3_month_key = (one_month_ago.year, one_month_ago.month)

    # ------------------------------------------------------------------
    # Expense window analyser
    # ------------------------------------------------------------------
    def _analyse_expense_window(window_txns, window_month_key):
        if not window_txns:
            return None

        repeat_flags = _find_suspicious_repeats(window_txns)

        # Category monthly spike — computed once per category for this window month
        cat_monthly_spike_cache = {}
        for cat in {t["category"] for t in window_txns}:
            cat_monthly_spike_cache[cat] = _category_monthly_spike_signal(
                cat, window_month_key, cat_monthly
            )

        anomalies = []
        for txn in window_txns:
            amt    = float(txn["amount"])
            txn_id = txn["id"]
            reasons = []

            # Signal 1 — Z-Score
            trig, score, detail = _z_score_signal(amt, cat_amounts.get(txn["category"], []))
            if trig:
                reasons.append({"signal": "amount_outlier", "detail": detail, "score": score})

            # Signal 2 — Category single-txn spike
            trig, score, detail = _category_spike_signal(
                amt, txn["category"], txn["date"], cat_monthly
            )
            if trig:
                reasons.append({"signal": "category_spike", "detail": detail, "score": score})

            # Signal 3 — Suspicious repeats
            if txn_id in repeat_flags:
                _, score, detail = repeat_flags[txn_id]
                reasons.append({"signal": "suspicious_repeat", "detail": detail, "score": score})

            # Signal 4 — Daily spike
            trig, score, detail = _daily_spike_signal(amt, daily_avg)
            if trig:
                reasons.append({"signal": "daily_spike", "detail": detail, "score": score})

            # Signal 5 — Category monthly total spike vs prior months
            trig, score, detail = cat_monthly_spike_cache.get(
                txn["category"], (False, 0.0, "")
            )
            if trig:
                reasons.append({"signal": "category_monthly_spike", "detail": detail, "score": score})

            # Signal 6 — LOF (ML, only when active)
            if txn_id in lof_results:
                score, detail = lof_results[txn_id]
                reasons.append({"signal": "lof", "detail": detail, "score": score})

            if reasons:
                anomalies.append({
                    "transaction_id":  txn_id,
                    "title":           txn["title"],
                    "amount":          amt,
                    "date":            txn["date"].isoformat(),
                    "category":        txn["category"],
                    "anomaly_score":   max(r["score"] for r in reasons),
                    "anomaly_reasons": reasons,
                    # True if LOF spotted something the rules alone missed
                    "ml_contributed":  any(r["signal"] == "lof" for r in reasons),
                })

        if not anomalies:
            return None
        anomalies.sort(key=lambda a: a["anomaly_score"], reverse=True)
        return anomalies

    # ------------------------------------------------------------------
    # Income window analyser (rule-based only — income is typically sparse)
    # ------------------------------------------------------------------
    def _analyse_income_window(income_window_txns):
        if not income_window_txns:
            return None
        anomalies = []
        for txn in income_window_txns:
            amt     = float(txn["amount"])
            reasons = []
            trig, score, detail = _income_spike_signal(amt, txn["date"], monthly_income)
            if trig:
                reasons.append({"signal": "income_spike", "detail": detail, "score": score})
            if reasons:
                anomalies.append({
                    "transaction_id":  txn["id"],
                    "title":           txn["title"],
                    "amount":          amt,
                    "date":            txn["date"].isoformat(),
                    "category":        txn["category"],
                    "anomaly_score":   max(r["score"] for r in reasons),
                    "anomaly_reasons": reasons,
                    "ml_contributed":  False,
                })
        if not anomalies:
            return None
        anomalies.sort(key=lambda a: a["anomaly_score"], reverse=True)
        return anomalies

    # ------------------------------------------------------------------
    # Return
    # ------------------------------------------------------------------
    return {
        "current_month":                  _analyse_expense_window(current_month_txns, current_month_key),
        "last_3_months":                  _analyse_expense_window(last_3_months_txns, last_3_month_key),
        "current_month_income_anomalies": _analyse_income_window(current_month_income),
        "last_3_months_income_anomalies": _analyse_income_window(last_3_months_income),
        # Metadata — useful for the UI
        "ml_active":               ml_active,
        "ml_min_samples_required": ML_MIN_SAMPLES,
        "user_total_expenses":     len(all_expenses),
    }