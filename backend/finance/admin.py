from django.contrib import admin
from finance.models import Transaction, Goal, AnomalousTransaction, MLResult
from import_export.admin import ExportMixin
from import_export import resources

# Register your models here.
class TransactionResource(resources.ModelResource):
    class Meta:
        model = Transaction
        fields = ('date', 'title', 'amount', 'transaction_type')


class TransactionAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = TransactionResource
    list_display = ('date', 'title', 'amount', 'transaction_type') 
    search_fields = ('title',)


class AnomalousTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'anomaly_score', 'period', 'is_dismissed', 'detected_at')
    list_filter = ('period', 'is_dismissed')
    search_fields = ('transaction__title',)


class MLResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'feature', 'computed_at')
    list_filter = ('feature',)
    search_fields = ('user__username',)
    readonly_fields = ('result',)


admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Goal)
admin.site.register(AnomalousTransaction, AnomalousTransactionAdmin)
admin.site.register(MLResult, MLResultAdmin)