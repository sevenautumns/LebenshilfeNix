from django.contrib import admin, messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.formats import number_format
from django.utils.html import format_html
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeNumericListFilter,
)
from django.utils import timezone
from django.db.models import Q
from unfold.admin import TabularInline
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from base.admin import (
    BaseModelAdmin,
    AddressInline,
    PhoneInline,
    EmailInline,
    BankAccountInline,
)
from base.admin_views import BaseApplyView, BaseCalculatorView
from .models import (
    Denomination,
    Employee,
    Absence,
    TrainingType,
    VocationalTraining,
    TrainingRecord,
    Employment,
    OtherEmployment,
    Applicant,
)


class OtherEmploymentInline(TabularInline):
    model = OtherEmployment
    extra = 0
    hide_title = True


class EmploymentCalculatorView(BaseCalculatorView):
    title = "Vergütungsrechner"

    def get_form_class(self):
        from .forms import CalculatorOverridesForm

        return CalculatorOverridesForm

    @classmethod
    def parse_overrides(cls, data: dict) -> dict:
        from decimal import Decimal
        from finance.models import SalaryAgreement

        overrides = {}
        if mo := data.get("months_override"):
            try:
                overrides["months_override"] = Decimal(mo)
            except Exception:
                pass
        if sa_pk := data.get("salary_agreement_override"):
            try:
                overrides["salary_agreement_override"] = SalaryAgreement.objects.get(
                    pk=int(sa_pk)
                )
            except Exception:
                pass
        return overrides

    @classmethod
    def overrides_to_params(cls, overrides: dict) -> dict:
        params = {}
        if mo := overrides.get("months_override"):
            params["months_override"] = str(mo)
        if sa := overrides.get("salary_agreement_override"):
            params["salary_agreement_override"] = str(sa.pk)
        return params

    def get_source_fields(self, obj: Employment):
        from base.fields import HourMinuteDurationField

        end = obj.end_date.strftime("%d.%m.%Y") if obj.end_date else "laufend"
        return [
            ("Mitarbeiter:in", str(obj.employee)),
            ("Art des Vertrags", obj.get_contract_type_display() or "—"),
            ("Zeitraum", f"{obj.start_date.strftime('%d.%m.%Y')} – {end}"),
            (
                "Wochenstunden",
                HourMinuteDurationField.format_std(obj.weekly_hours),
            ),
        ]

    def get_primary_results(self, obj: Employment, result):
        i = result.input
        override_params = self.overrides_to_params(
            {
                "months_override": i.months_override,
                "salary_agreement_override": i.salary_agreement_override,
            }
        )
        apply_url = self.build_apply_url(
            obj, "admin:hr_employment_calculator_apply", override_params
        )

        return [
            {
                "label": "Monatsbrutto (berechnet)",
                "value": result.monthly_gross_salary,
                "unit": "€",
                "stored_label": "Gespeichertes Monatsbrutto",
                "stored_value": obj.gross_salary,
                "apply_url": apply_url
                if result.monthly_gross_salary is not None
                else None,
            },
            {
                "label": "Jahresbrutto",
                "value": result.yearly_gross_salary,
                "unit": "€",
                "stored_label": None,
                "stored_value": None,
                "apply_url": None,
            },
        ]

    def get_result_rows(self, obj: Employment, result):
        from django.utils.formats import number_format

        return [
            (
                "Tarifvertrag",
                str(result.salary_agreement) if result.salary_agreement else "—",
                False,
            ),
            (
                "Monate (rechnerisch)",
                number_format(result.calculated_months, decimal_pos=1, use_l10n=True)
                if result.calculated_months is not None
                else "—",
                False,
            ),
            (
                "Effektive Monate",
                number_format(result.effective_months, decimal_pos=1, use_l10n=True)
                if result.effective_months is not None
                else "—",
                result.effective_months != result.calculated_months,
            ),
        ]

    def run_calculation(self, obj: Employment, overrides: dict):
        from .calculators import CalculatorInput, run_calculation as _run_calculation

        return _run_calculation(
            CalculatorInput(
                start_date=obj.start_date,
                end_date=obj.end_date,
                weekly_hours=obj.weekly_hours,
                contract_type=obj.contract_type,
                **overrides,
            )
        )


class EmploymentApplySalaryView(BaseApplyView):
    title = "Vergütungsrechner"
    calculator_url_name = "admin:hr_employment_calculator"
    calculator_view_class = EmploymentCalculatorView

    def get_queryset(self):
        return Employment.objects.select_related("employee")

    def run_calculation(self, obj: Employment, overrides: dict):
        from .calculators import CalculatorInput, run_calculation as _run_calculation

        return _run_calculation(
            CalculatorInput(
                start_date=obj.start_date,
                end_date=obj.end_date,
                weekly_hours=obj.weekly_hours,
                contract_type=obj.contract_type,
                **overrides,
            )
        )

    def get_value(self, result):
        return result.monthly_gross_salary

    def save_value(self, obj: Employment, value) -> None:
        obj.gross_salary = value
        obj.save(update_fields=["gross_salary"])

    def error_message(self) -> str:
        return "Brutto konnte nicht berechnet werden — keine Übernahme möglich."

    def success_message(self, formatted: str) -> str:
        return f"Brutto übernommen: {formatted} €"


@admin.register(Employee)
class EmployeeAdmin(BaseModelAdmin):
    list_display = ("full_name", "personnel_number", "birthday", "citizenship")
    search_fields = ("first_name", "last_name")
    filter_horizontal = ("vocational_trainings",)
    autocomplete_fields = ("church_membership",)
    list_filter = (["citizenship", ChoicesDropdownFilter],)

    inlines = [
        OtherEmploymentInline,
        AddressInline,
        PhoneInline,
        EmailInline,
        BankAccountInline,
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("church_membership")


@admin.register(Employment)
class EmploymentAdmin(BaseModelAdmin):
    list_display = (
        "employee",
        "contract_type",
        "start_date",
        "end_date",
        "weekly_hours",
        "display_gross_salary",
    )
    actions_detail = ["edit_action", "calculator_action"]
    search_fields = (
        "employee__first_name",
        "employee__last_name",
        "employee__personnel_number",
    )
    autocomplete_fields = ("employee",)
    list_filter_submit = True
    list_filter = (("start_date", RangeDateFilter), ("end_date", RangeDateFilter))
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "employee",
                    "contract_type",
                    ("start_date", "end_date"),
                    "weekly_hours",
                    "gross_salary",
                ]
            },
        ),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("employee")

    @action(
        description="Vergütungsrechner",
        url_path="calculator-action",
        permissions=["calculator_action"],
        variant=ActionVariant.DEFAULT,
    )
    def calculator_action(self, request, object_id: int):
        return redirect(reverse("admin:hr_employment_calculator", args=[object_id]))

    def has_calculator_action_permission(self, request, obj=None):
        return True

    @display(description="Brutto laut Vertrag", ordering="gross_salary")
    def display_gross_salary(self, obj: Employment):
        if obj.gross_salary is not None:
            from django.utils import formats

            formatted = formats.number_format(
                obj.gross_salary, decimal_pos=2, use_l10n=True
            )
            return format_html("{} €", formatted)
        url = reverse("admin:hr_employment_calculator", args=[obj.pk])
        return format_html('<a href="{}">Berechnen →</a>', url)

    @display(description="Rechner")
    def calculator_link(self, obj: Employment):
        url = reverse("admin:hr_employment_calculator", args=[obj.pk])
        return format_html('<a href="{}">Berechnen →</a>', url)

    def get_urls(self):
        custom = [
            path(
                "<int:pk>/calculator/",
                self.admin_site.admin_view(
                    EmploymentCalculatorView.as_view(model_admin=self)
                ),
                name="hr_employment_calculator",
            ),
            path(
                "<int:pk>/calculator/apply/",
                self.admin_site.admin_view(
                    EmploymentApplySalaryView.as_view(model_admin=self)
                ),
                name="hr_employment_calculator_apply",
            ),
        ]
        return custom + super().get_urls()


@admin.register(Absence)
class AbsenceAdmin(BaseModelAdmin):
    list_display = ("employee", "reason", "start_date", "end_date", "certificate")
    list_filter = ("reason", "certificate")
    search_fields = ("employee__first_name", "employee__last_name")
    autocomplete_fields = ("employee",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("employee")


class TrainingValidityFilter(admin.SimpleListFilter):
    title = "Gültig"
    parameter_name = "is_valid"

    def lookups(self, request, model_admin):
        return (
            ("True", "Ja"),
            ("False", "Nein"),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        val = self.value()

        if val == "True":
            return queryset.filter(valid_from__lte=today).filter(
                Q(valid_to__isnull=True) | Q(valid_to__gte=today)
            )

        if val == "False":
            return queryset.filter(Q(valid_from__gt=today) | Q(valid_to__lt=today))

        return queryset


@admin.register(TrainingRecord)
class TrainingRecordAdmin(BaseModelAdmin):
    list_display = ("employee", "training_type", "valid_from", "valid_to", "valid")
    autocomplete_fields = ("employee", "training_type")
    list_filter = (TrainingValidityFilter, "employee", "training_type__name")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("employee", "training_type")

    @admin.display(description="Gültig", boolean=True, ordering="valid_to")
    def valid(self, obj):
        return obj.is_valid


@admin.register(TrainingType)
class TrainingTypeAdmin(BaseModelAdmin):
    search_fields = ("name",)


@admin.register(VocationalTraining)
class VocationalTrainingAdmin(BaseModelAdmin):
    list_display = ("name", "qualified")
    list_filter = [("qualified", BooleanRadioFilter)]
    search_fields = ("name",)


class DesiredHoursRangeFilter(RangeNumericListFilter):
    parameter_name = "desired_hours"
    title = "Stundenwunsch"

    def queryset(self, request, queryset):
        min_val = self.used_parameters.get(f"{self.parameter_name}_from")
        max_val = self.used_parameters.get(f"{self.parameter_name}_to")
        if min_val:
            queryset = queryset.filter(desired_hours_max__gte=min_val)
        if max_val:
            queryset = queryset.filter(desired_hours_min__lte=max_val)
        return queryset


@admin.register(Applicant)
class ApplicantAdmin(BaseModelAdmin):
    list_display = (
        "full_name",
        "application_date",
        "notice_period_months",
        "earliest_start_date",
        "desired_hours_display",
        "desired_school",
    )
    search_fields = ("first_name", "last_name")
    autocomplete_fields = ("desired_school",)
    list_filter = (
        ("earliest_start_date", RangeDateFilter),
        DesiredHoursRangeFilter,
        ["desired_school", AutocompleteSelectFilter],
    )
    list_filter_submit = True
    inlines = [
        AddressInline,
        PhoneInline,
        EmailInline,
        BankAccountInline,
    ]

    @admin.display(description="Stundenwunsch")
    def desired_hours_display(self, obj):
        return obj.desired_hours_summary


@admin.register(Denomination)
class DenominationAdmin(BaseModelAdmin):
    search_fields = ("name",)
