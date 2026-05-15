from django.urls import path
from finance.views.base_views import (
    RegisterView, DashboardView, TransactionView, TransactionListView,
    GoalView, LoginView, LogoutView, BulkTransactionView
)
from finance.views.recurring_txn_view import RecurringTransactionView




urlpatterns = [
    path('register/', RegisterView.as_view(), name="register"),
    path('login', LoginView.as_view(), name="login"),
    path('logout', LogoutView.as_view(), name="logout"),
    path('dashboard', DashboardView.as_view(), name="dashboard"),
    path('transaction', TransactionView.as_view(), name="transaction"),
    path('transaction/list', TransactionListView.as_view(), name="transaction_list"),
    path('transaction/bulk', BulkTransactionView.as_view(), name="transaction_bulk"),
    path('goal', GoalView.as_view(), name="goal"),
    path('recurring', RecurringTransactionView.as_view(), name="recurring_transactions"),
   # path('generate-report', export_transactions, name="export_transactions"),
    
]

