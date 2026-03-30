from django.contrib import admin
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from base.admin import BaseModelAdmin
from .models import SalaryAgreement, CostPayer, CostPayerContact, FeeAgreement, PoolAgreement, Payment


@admin.register(SalaryAgreement)
class SalaryAgreementAdmin(BaseModelAdmin):
    list_display = ("valid_from", "valid_to", "salary_standard")
    search_fields = ("valid_from", "valid_to")
    list_filter_submit = True
    list_filter = (("valid_from", RangeDateFilter), ("valid_to", RangeDateFilter))


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
    list_filter_submit = True
    list_filter = (("valid_from", RangeDateFilter), ("valid_to", RangeDateFilter))

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("responsible_payer")


@admin.register(PoolAgreement)
class PoolAgreementAdmin(BaseModelAdmin):
    list_display = ("school", "payer", "flat_rate", "approved_supervisions", "prophylactic_supervisions", "valid_from", "valid_to")
    list_filter = ("school", "payer")
    search_fields = ("payer__identifier", "school__name")
    autocomplete_fields = ("payer", "school")
    date_hierarchy = "valid_from"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer", "school")


@admin.register(Payment)
class PaymentAdmin(BaseModelAdmin):
    list_display = ("payer", "amount", "payment_date", "supervision")
    list_filter_submit = True
    list_filter = (("payment_date", RangeDateFilter), "payer")
    autocomplete_fields = ("payer", "supervision")
    search_fields = ("payer__identifier", "note")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("payer", "supervision__student")
        )
