from django.contrib import admin
from unfold.admin import TabularInline
from base.admin import BaseModelAdmin
from .models import SalaryAgreement, CostPayer, CostPayerContact, FeeAgreement, PoolAgreement, Payment


@admin.register(SalaryAgreement)
class SalaryAgreementAdmin(BaseModelAdmin):
    list_display = ("valid_from", "valid_to", "salary_standard")
    list_filter = ("valid_from", "valid_to")


class CostPayerContactInline(TabularInline):
    model = CostPayerContact
    extra = 0


@admin.register(CostPayer)
class CostPayerAdmin(BaseModelAdmin):
    list_display = ("identifier",)
    search_fields = ("identifier",)
    inlines = [CostPayerContactInline]


@admin.register(FeeAgreement)
class FeeAgreementAdmin(BaseModelAdmin):
    list_display = ("responsible_payer", "valid_from", "valid_to")
    filter_horizontal = ("additional_payers",)
    search_fields = ("responsible_payer__identifier",)
    autocomplete_fields = ("responsible_payer",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("responsible_payer")


@admin.register(PoolAgreement)
class PoolAgreementAdmin(BaseModelAdmin):
    list_display = ("payer", "flat_rate", "max_supervisions", "valid_from", "valid_to")
    list_filter = ("payer",)
    search_fields = ("payer__identifier",)
    autocomplete_fields = ("payer",)
    date_hierarchy = "valid_from"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer")


@admin.register(Payment)
class PaymentAdmin(BaseModelAdmin):
    list_display = ("payer", "amount", "payment_date", "supervision")
    list_filter = ("payment_date", "payer")
    autocomplete_fields = ("payer", "supervision")
    search_fields = ("payer__identifier", "note")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("payer", "supervision__student")
        )
