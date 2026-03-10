from django.contrib import admin
from base.admin import BaseModelAdmin, CostPayerLinkInline
from .models import CostPayer, FeeAgreement, PoolAgreement, Payment

@admin.register(CostPayer)
class CostPayerAdmin(BaseModelAdmin):
    search_fields = ('identifier',)

@admin.register(FeeAgreement)
class FeeAgreementAdmin(BaseModelAdmin):
    list_display = ('valid_from', 'valid_to')
    inlines = [CostPayerLinkInline]

@admin.register(PoolAgreement)
class PoolAgreementAdmin(BaseModelAdmin):
    autocomplete_fields = ('payer',)

@admin.register(Payment)
class PaymentAdmin(BaseModelAdmin):
    list_display = ('payer', 'amount', 'payment_date', 'supervision')
    list_filter = ('payment_date', 'payer')
    autocomplete_fields = ('payer','supervision')
    search_fields = ('payer__identifier', 'note')
