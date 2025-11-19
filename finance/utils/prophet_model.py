# finance/utils/prophet_model.py
import pandas as pd
from prophet import Prophet
import os
import joblib

MODEL_DIR = "finance/ml_models"
os.makedirs(MODEL_DIR, exist_ok=True)

def train_prophet(monthly_df, user_id=None):
    """
    monthly_df: pandas DataFrame with columns ['month','total'] where month is datetime
    returns: trained Prophet model
    """
    df = monthly_df.copy()
    df = df.rename(columns={"month": "ds", "total": "y"})[["ds", "y"]]
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    model.fit(df)
    # optionally save
    if user_id:
        path = os.path.join(MODEL_DIR, f"prophet_user_{user_id}.pkl")
        joblib.dump(model, path)
    return model

def predict_prophet(model, periods=1, freq='M'):
    future = model.make_future_dataframe(periods=periods, freq=freq)
    forecast = model.predict(future)
    # return the last forecasted yhat for the next period(s)
    return forecast.iloc[-periods:]['yhat'].values
