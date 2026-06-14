from django.db import models
from finance.models.base_models import User

class RecurringTransaction(models.Model):
    RECURRING_TYPES = [
        ('Salary', 'Salary'),
        ('Rent', 'Rent'),
        ('Subscription', 'Subscription'),
        ('EMI', 'EMI'),
        ('Bill', 'Bill'),
        ('Regular Transfer', 'Regular Transfer'),
    ]
    INTERVAL_BUCKETS = [
        ('15_days', '15 Days'),
        ('30_days', '30 Days'),
        ('90_days', '90 Days'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interval_bucket = models.CharField(max_length=10, choices=INTERVAL_BUCKETS)
    mean_gap_days = models.FloatField()
    confidence = models.FloatField()
    next_expected_date = models.DateField(null=True, blank=True)
    recurring_type = models.CharField(max_length=50, choices=RECURRING_TYPES)
    occurrences = models.IntegerField()
    last_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'title', 'amount', 'interval_bucket')
        ordering = ['-confidence']

    def __str__(self):
        return f"{self.title} - {self.interval_bucket} ({self.recurring_type})"