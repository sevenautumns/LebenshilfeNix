from django.template.response import TemplateResponse
from django.urls import path
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
    )
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

    def get_urls(self):
        custom = [
            path(
                "calculator/",
                self.admin_site.admin_view(self.calculator_view),
                name="hr_employment_calculator",
            ),
        ]
        return custom + super().get_urls()

    def calculator_view(self, request):
        from .calculators import CalculatorInput, run_calculation
        from .forms import SalaryCalculatorForm

        result = None
        form = SalaryCalculatorForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            cd = form.cleaned_data
            result = run_calculation(
                CalculatorInput(
                    start_date=cd["start_date"],
                    end_date=cd.get("end_date"),
                    weekly_hours=cd["weekly_hours"],
                    contract_type=cd["contract_type"],
                    month_override=cd.get("month_override"),
                    work_days_override=cd.get("work_days_override"),
                )
            )

        context = self.admin_site.each_context(request)
        context |= {
            "title": "Vergütungsrechner",
            "form": form,
            "result": result,
            "opts": self.model._meta,
            "media": self.media + form.media,
        }
        return TemplateResponse(request, "admin/hr/employment/calculator.html", context)


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
