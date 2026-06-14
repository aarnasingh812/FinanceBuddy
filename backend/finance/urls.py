from django.urls import path
from finance.views.base_views import (
    RegisterView, TransactionView, TransactionListView,
    GoalView, GoalListView, LoginView, LogoutView, BulkTransactionView,
)
from finance.views.dashboard_view import DashboardView
from finance.views.recurring_txn_view import RecurringTransactionView
from finance.views.anomaly_view import AnomalyDetectionView
from finance.views.goal_forecast_view import GoalForecastView
from finance.views.recommendation_view import RecommendationView
from finance.views.ml_compute_view import MLComputeView
from finance.views.ml_compute_status_view import MLComputeStatusView





urlpatterns = [
    path('register/', RegisterView.as_view(), name="register"),
    path('login', LoginView.as_view(), name="login"),
    path('logout', LogoutView.as_view(), name="logout"),
    path('dashboard', DashboardView.as_view(), name="dashboard"),
    path('transaction', TransactionView.as_view(), name="transaction"),
    path('transaction/list', TransactionListView.as_view(), name="transaction_list"),
    path('transaction/bulk', BulkTransactionView.as_view(), name="transaction_bulk"),
    path('goal', GoalView.as_view(), name="goal"),
    path('goal/list', GoalListView.as_view(), name="goal_list"),
    path('recurring', RecurringTransactionView.as_view(), name="recurring_transactions"),
    path('anomalies', AnomalyDetectionView.as_view(), name="anomalies"),
    path('goal/forecast', GoalForecastView.as_view(), name="goal_forecast"),
    path('recommendations', RecommendationView.as_view(), name="recommendations"),
    path('ml/compute', MLComputeView.as_view(), name="ml_compute"),
    path('ml/compute/status/<str:task_id>', MLComputeStatusView.as_view(), name="ml_compute_status"),
   # path('generate-report', export_transactions, name="export_transactions"),
    
]


