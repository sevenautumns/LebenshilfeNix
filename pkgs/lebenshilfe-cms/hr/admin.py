from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeNumericListFilter,
)
from django.contrib import admin
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
        "gross_salary",
        "calculator_link",
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

    @display(description="Rechner")
    def calculator_link(self, obj: Employment):
        url = reverse("admin:hr_employment_calculator", args=[obj.pk])
        return format_html('<a href="{}">Berechnen →</a>', url)

    def get_urls(self):
        custom = [
            path(
                "<int:pk>/calculator/",
                self.admin_site.admin_view(self.calculator_view),
                name="hr_employment_calculator",
            ),
            path(
                "<int:pk>/calculator/apply/",
                self.admin_site.admin_view(self.apply_salary_view),
                name="hr_employment_calculator_apply",
            ),
        ]
        return custom + super().get_urls()

    def calculator_view(self, request, pk: int):
        from base.fields import HourMinuteDurationField
        from .calculators import CalculatorInput, run_calculation
        from .forms import CalculatorOverridesForm

        try:
            employment = Employment.objects.select_related("employee").get(pk=pk)
        except Employment.DoesNotExist:
            raise Http404

        form = CalculatorOverridesForm(request.POST or None)
        month_override = None
        salary_agreement_override = None
        if request.method == "POST" and form.is_valid():
            month_override = form.cleaned_data.get("month_override")
            salary_agreement_override = form.cleaned_data.get(
                "salary_agreement_override"
            )

        result = run_calculation(
            CalculatorInput(
                start_date=employment.start_date,
                end_date=employment.end_date,
                weekly_hours=employment.weekly_hours,
                contract_type=employment.contract_type,
                month_override=month_override,
                salary_agreement_override=salary_agreement_override,
            )
        )

        end = (
            employment.end_date.strftime("%d.%m.%Y")
            if employment.end_date
            else "laufend"
        )
        opts = self.model._meta
        apply_url = reverse("admin:hr_employment_calculator_apply", args=[pk])
        source_fields = [
            ("Mitarbeiter:in", str(employment.employee)),
            ("Art des Vertrags", employment.get_contract_type_display() or "—"),
            ("Zeitraum", f"{employment.start_date.strftime('%d.%m.%Y')} – {end}"),
            (
                "Wochenstunden",
                HourMinuteDurationField.format_std(employment.weekly_hours),
            ),
        ]
        primary_results = [
            {
                "label": "Monatsbrutto (berechnet)",
                "value": result.monthly_gross_salary,
                "unit": "€",
                "stored_label": "Aktuell gespeichert",
                "stored_value": employment.gross_salary,
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
        result_rows = [
            (
                "Tarifvertrag",
                str(result.salary_agreement) if result.salary_agreement else "—",
                False,
            ),
            ("Monate (rechnerisch)", result.calculated_months, False),
            (
                "Effektive Monate",
                result.effective_months,
                result.effective_months != result.calculated_months,
            ),
        ]
        breadcrumb_items = [
            {
                "label": opts.app_config.verbose_name,
                "url": reverse("admin:app_list", kwargs={"app_label": opts.app_label}),
            },
            {
                "label": str(opts.verbose_name_plural).capitalize(),
                "url": reverse("admin:hr_employment_changelist"),
            },
            {
                "label": str(employment),
                "url": reverse("admin:hr_employment_change", args=[employment.pk]),
            },
            {"label": "Vergütungsrechner", "url": None},
        ]

        context = self.admin_site.each_context(request)
        context |= {
            "title": "Vergütungsrechner",
            "employment": employment,
            "form": form,
            "source_fields": source_fields,
            "primary_results": primary_results,
            "result_rows": result_rows,
            "warnings": result.warnings,
            "breadcrumb_items": breadcrumb_items,
            "opts": opts,
            "media": self.media + form.media,
        }
        return TemplateResponse(request, "admin/calculator_base.html", context)

    def apply_salary_view(self, request, pk: int):
        from django.contrib import messages
        from .calculators import CalculatorInput, run_calculation

        if request.method != "POST":
            return redirect("admin:hr_employment_calculator", pk)

        try:
            employment = Employment.objects.select_related("employee").get(pk=pk)
        except Employment.DoesNotExist:
            raise Http404

        result = run_calculation(
            CalculatorInput(
                start_date=employment.start_date,
                end_date=employment.end_date,
                weekly_hours=employment.weekly_hours,
                contract_type=employment.contract_type,
            )
        )

        if result.monthly_gross_salary is None:
            messages.error(
                request,
                "Brutto konnte nicht berechnet werden — keine Übernahme möglich.",
            )
        else:
            employment.gross_salary = result.monthly_gross_salary
            employment.save(update_fields=["gross_salary"])
            from django.utils.formats import number_format

            formatted = number_format(
                result.monthly_gross_salary, decimal_pos=2, use_l10n=True
            )
            messages.success(request, f"Brutto übernommen: {formatted} €")

        return redirect(reverse("admin:hr_employment_calculator", args=[pk]))


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
