from django.db import models
from finance.models.base_models import User


class MLResult(models.Model):
    FEATURE_CHOICES = [
        ('recurring', 'Recurring Transactions'),
        ('anomaly', 'Anomaly Detection'),
        ('forecast', 'Goal Forecast'),
        ('recommendation', 'Recommendations & Insights'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ml_results')
    feature = models.CharField(max_length=20, choices=FEATURE_CHOICES)
    result = models.JSONField()
    status = models.BooleanField(default=True)   # True (1) = current, False (0) = old
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-computed_at']
        indexes = [
            models.Index(fields=['user', 'feature', '-computed_at']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.feature} — {self.computed_at}"

