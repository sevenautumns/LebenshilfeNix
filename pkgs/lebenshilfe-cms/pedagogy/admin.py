from django.contrib import admin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display
from base.admin import BaseModelAdmin, AddressInline, PhoneInline, EmailInline
from base.fields import HourMinuteDurationField, EuroDecimalField
from .models import School, Student, Supervision, Request

_duration_fmt = HourMinuteDurationField()
_euro_fmt = EuroDecimalField(max_digits=10, decimal_places=2)


@admin.register(Student)
class StudentAdmin(BaseModelAdmin):
    list_display = ("full_name", "payer")
    search_fields = ("first_name", "last_name")
    inlines = [AddressInline, PhoneInline, EmailInline]
    autocomplete_fields = ("payer",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer")


@admin.register(Supervision)
class SupervisionAdmin(BaseModelAdmin):
    list_display = (
        "student",
        "tandem",
        "caretaker",
        "school",
        "start_date",
        "end_date",
        "weekly_hours",
        "is_prophylactic",
        "display_tandem_prophylactic",
    )
    list_filter_submit = True
    list_filter = ("school", ("start_date", RangeDateFilter))
    search_fields = ("student__first_name", "student__last_name")
    autocomplete_fields = ("student", "tandem", "caretaker", "school")
    readonly_fields = (
        "calculated_school_days",
        "display_daily_hours",
        "display_total_hours",
        "fee_agreement",
        "display_total_amount",
        "display_monthly_installment",
    )
    conditional_fields = {"is_tandem_prophylactic": "!!tandem"}
    fieldsets = [
        ("Schüler:in", {"fields": [("student", "is_prophylactic")]}),
        ("Tandem", {"fields": [("tandem", "is_tandem_prophylactic")]}),
        ("Betreuung", {"fields": ["caretaker", ("school", "class_name")]}),
        (
            "Zeitraum & Stunden",
            {
                "fields": [
                    ("start_date", "end_date"),
                    ("weekly_hours", "display_daily_hours"),
                    ("calculated_school_days", "school_days_override"),
                    "display_total_hours",
                ]
            },
        ),
        (
            "Abrechnung",
            {
                "fields": [
                    "fee_agreement",
                    ("display_total_amount", "display_monthly_installment"),
                ]
            },
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return super().get_readonly_fields(request, obj)

    @display(description="Tandem prophylaktisch", boolean=True)
    def display_tandem_prophylactic(self, obj: Supervision) -> bool | None:
        if not obj.tandem_id:
            return None
        return obj.is_tandem_prophylactic

    @display(description="Stunden pro Tag")
    def display_daily_hours(self, obj: Supervision) -> str:
        return _duration_fmt.get_admin_format(obj.daily_hours)

    @display(description="Gesamtstunden")
    def display_total_hours(self, obj: Supervision) -> str:
        return _duration_fmt.get_admin_format(obj.total_hours)

    @display(description="Gesamtbetrag")
    def display_total_amount(self, obj: Supervision) -> str:
        return _euro_fmt.get_admin_format(obj.total_amount)

    @display(description="Abschlag pro Monat")
    def display_monthly_installment(self, obj: Supervision) -> str:
        return _euro_fmt.get_admin_format(obj.monthly_installment)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("student", "caretaker", "school", "tandem")
        )


@admin.register(Request)
class RequestAdmin(BaseModelAdmin):
    list_display = ("student", "state", "start_date", "demand", "review_date")
    list_filter = ("state",)
    search_fields = ("student__first_name", "student__last_name", "notes")
    autocomplete_fields = ("student", "school")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student", "school")


@admin.register(School)
class SchoolAdmin(BaseModelAdmin):
    search_fields = ("name",)
