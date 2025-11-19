# finance/utils/forecasting.py
import pandas as pd
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from finance.models import Transaction
from .prophet_model import train_prophet, predict_prophet
# from .lstm_model import train_lstm, predict_lstm   # optional if you want LSTM
import os

MIN_MONTHS = 6   # threshold for ML forecasting
COLD_START_EXPENSE_RATIO = 0.75  # default expense as fraction of income

def _get_monthly_df(user, trans_type):
    qs = (
        Transaction.objects
        .filter(user=user, transaction_type=trans_type)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    df = pd.DataFrame(list(qs))
    # ensure month dtype
    if not df.empty:
        df['month'] = pd.to_datetime(df['month'])
    return df

def ml_forecast_next_month(user, trans_type, method='prophet', user_id=None):
    """
    Returns predicted value (float) for next month for given trans_type ('Income'/'Expense').
    method: 'prophet' or 'lstm'
    """
    df = _get_monthly_df(user, trans_type)

    # Cold-start: not enough data
    if df.shape[0] < MIN_MONTHS:
        return cold_start_prediction(user, trans_type, df)

    # Use Prophet by default
    if method == 'prophet':
        # train and predict
        model = train_prophet(df, user_id=user_id)
        yhat = predict_prophet(model, periods=1)[0]
        return float(yhat)

    # Optional LSTM path (commented unless you enable it)
    # elif method == 'lstm':
    #     model, scaler = train_lstm(df, user_id=user_id)
    #     preds = predict_lstm(model, scaler, df, seq_len=6, steps=1)
    #     return float(preds[0])

    # fallback
    return cold_start_prediction(user, trans_type, df)


def cold_start_prediction(user, trans_type, df):
    """
    If not enough months, produce a fallback prediction.
    Strategy:
      1. If user has a profile field 'monthly_income' or 'monthly_expense' return that
      2. Else if at least 1 month exists, use last-month value
      3. Else use generic default 0
    Expense prediction uses a ratio if no explicit expense
    """
    # try to use profile attribute if present
    profile = getattr(user, "profile", None)  # if you have a UserProfile model
    if trans_type == "Income":
        if profile and getattr(profile, "monthly_income", None):
            return float(profile.monthly_income)
    else:
        if profile and getattr(profile, "monthly_expense", None):
            return float(profile.monthly_expense)

    # if we have at least 1 month, use average or last month
    if not df.empty:
        # prefer 3-month average if possible
        if df.shape[0] >= 3:
            return float(df['total'].tail(3).mean())
        return float(df['total'].iloc[-1])

    # as a last resort: if requesting Expense but no data, tie to income template
    if trans_type == "Expense":
        # attempt to infer from income (if any)
        income_df = _get_monthly_df(user, "Income")
        if not income_df.empty:
            last_income = float(income_df['total'].iloc[-1])
            return last_income * COLD_START_EXPENSE_RATIO

    # otherwise 0
    return 0.0
