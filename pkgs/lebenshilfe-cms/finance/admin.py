from django.contrib import admin
from base.admin import BaseModelAdmin
from .models import CostPayer, FeeAgreement, PoolAgreement, Payment


@admin.register(CostPayer)
class CostPayerAdmin(BaseModelAdmin):
    list_display = ("identifier",)
    search_fields = ("identifier",)


@admin.register(FeeAgreement)
class FeeAgreementAdmin(BaseModelAdmin):
    list_display = ("label", "responsible_payer", "valid_from", "valid_to")
    currency_fields = ("price_standard", "price_tandem", "price_coordination")
    filter_horizontal = ("additional_payers",)
    autocomplete_fields = ("responsible_payer",)


@admin.register(PoolAgreement)
class PoolAgreementAdmin(BaseModelAdmin):
    list_display = ("payer", "flat_rate", "max_supervisions", "valid_from", "valid_to")
    list_filter = ("payer",)
    search_fields = ("payer__identifier",)
    autocomplete_fields = ("payer",)
    currency_fields = ("flat_rate",)
    date_hierarchy = "valid_from"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer")


@admin.register(Payment)
class PaymentAdmin(BaseModelAdmin):
    list_display = ("payer", "amount", "payment_date", "supervision")
    list_filter = ("payment_date", "payer")
    autocomplete_fields = ("payer", "supervision")
    search_fields = ("payer__identifier", "note")
    currency_fields = ("amount",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer", "supervision__student")
