from celery import shared_task
from django.contrib.auth import get_user_model
from finance.utils.forecasting import _get_monthly_df
from finance.utils.prophet_model import train_prophet
# from finance.utils.lstm_model import train_lstm  # optional

User = get_user_model()

@shared_task
def retrain_forecasting_models():
    users = User.objects.all()
    for user in users:
        for trans_type in ["Income", "Expense"]:
            df = _get_monthly_df(user, trans_type)
            if df.shape[0] >= 6:  # only retrain when enough history
                train_prophet(df, user_id=user.id)
