from django.db import models
from finance.models.base_models import User, Transaction


class AnomalousTransaction(models.Model):
    PERIOD_CHOICES = [
        ('current_month', 'Current Month'),
        ('last_3_months', 'Last 3 Months'),
        ('income_current_month', 'Income Current Month'),
        ('income_last_3_months', 'Income Last 3 Months'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anomalous_transactions')
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='anomaly_flags')
    anomaly_score = models.FloatField()        # 0.0 – 1.0
    signals = models.JSONField()               # list of {signal, detail, score}
    period = models.CharField(max_length=50, choices=PERIOD_CHOICES)
    is_dismissed = models.BooleanField(default=False)
    detected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'transaction', 'period')
        ordering = ['-anomaly_score']

    def __str__(self):
        return f"Anomaly: {self.transaction.title} (score={self.anomaly_score})"
