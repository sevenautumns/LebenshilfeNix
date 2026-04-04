from django.contrib import admin
from unfold.admin import TabularInline
from django.utils.translation import gettext_lazy as _
from unfold.contrib.filters.admin import RangeDateFilter
from base.admin import BaseModelAdmin
from .models import (
    SalaryAgreement,
    CostPayer,
    CostPayerContact,
    FeeAgreement,
    PoolAgreement,
    Payment,
    MonthlyContractCost,
)


class GrossPersonnelCostsFilter(admin.SimpleListFilter):
    title = "Brutto eingetragen"
    parameter_name = "brutto_eingetragen"

    def lookups(self, request, model_admin):
        return [
            ("ja", "Ja"),
            ("nein", "Nein"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "ja":
            return queryset.filter(gross_personnel_costs__isnull=False)
        if self.value() == "nein":
            return queryset.filter(gross_personnel_costs__isnull=True)
        return queryset


@admin.register(SalaryAgreement)
class SalaryAgreementAdmin(BaseModelAdmin):
    list_display = (
        "valid_from",
        "valid_to",
        "salary_standard",
        "salary_tandem",
        "salary_coordination",
    )
    search_fields = ("valid_from", "valid_to")
    list_filter_submit = True
    list_filter = (("valid_from", RangeDateFilter), ("valid_to", RangeDateFilter))


class CostPayerContactInline(TabularInline):
    model = CostPayerContact
    extra = 0
    hide_title = True


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
    list_display = (
        "school",
        "payer",
        "flat_rate",
        "approved_supervisions",
        "prophylactic_supervisions",
        "valid_from",
        "valid_to",
    )
    list_filter = ("school", "payer")
    search_fields = ("payer__identifier", "school__name")
    autocomplete_fields = ("payer", "school")
    date_hierarchy = "valid_from"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer", "school")


@admin.register(Payment)
class PaymentAdmin(BaseModelAdmin):
    list_display = ("payer", "amount", "billing_period", "supervision")
    list_filter_submit = True
    list_filter = (("billing_period", RangeDateFilter), "payer")
    autocomplete_fields = ("payer", "supervision")
    search_fields = ("payer__identifier", "note", "booking_number")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("payer", "supervision__student")
        )


@admin.register(MonthlyContractCost)
class MonthlyContractCostAdmin(BaseModelAdmin):
    list_display = ("employment", "billing_period", "gross_personnel_costs")
    list_filter_submit = True
    list_filter = (("billing_period", RangeDateFilter), GrossPersonnelCostsFilter)
    autocomplete_fields = ("employment",)
    search_fields = (
        "employment__employee__first_name",
        "employment__employee__last_name",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("employment__employee")
