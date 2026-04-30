from django.urls import path
from finance.views.views import (
    RegisterView, DashboardView, TransactionView, TransactionListView,
    GoalView, LoginView, LogoutView, BulkTransactionView,
)



urlpatterns = [
    path('register/', RegisterView.as_view(), name="register"),
    path('login', LoginView.as_view(), name="login"),
    path('logout', LogoutView.as_view(), name="logout"),
    path('dashboard', DashboardView.as_view(), name="dashboard"),
    path('transaction', TransactionView.as_view(), name="transaction"),
    path('transaction/list', TransactionListView.as_view(), name="transaction_list"),
    path('transaction/bulk', BulkTransactionView.as_view(), name="transaction_bulk"),
    path('goal', GoalView.as_view(), name="goal"),
   # path('generate-report', export_transactions, name="export_transactions"),
    
]

