from django.contrib import admin
from base.admin import BaseModelAdmin, AddressInline, PhoneInline, EmailInline
from .models import School, Student, Supervision, Request, PoolSchoolAgreement


@admin.register(Student)
class StudentAdmin(BaseModelAdmin):
    list_display = ("full_name", "payer")
    search_fields = ("first_name", "last_name")
    inlines = [AddressInline, PhoneInline, EmailInline]
    autocomplete_fields = ("payer",)


@admin.register(Supervision)
class SupervisionAdmin(BaseModelAdmin):
    hour_minute_fields = ("weekly_hours",)
    display_weekly_hours = BaseModelAdmin.duration_display(
        "weekly_hours", description="Wochenstunden"
    )
    list_display = (
        "student",
        "caretaker",
        "school",
        "start",
        "end",
        "display_weekly_hours",
    )
    list_filter = ("school", "start")
    search_fields = ("student__first_name", "student__last_name")
    autocomplete_fields = ("student", "tandem", "caretaker", "school")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student", "caretaker", "school", "tandem")


@admin.register(Request)
class RequestAdmin(BaseModelAdmin):
    hour_minute_fields = ("demand",)
    display_demand = BaseModelAdmin.duration_display(
        "demand", description="Bedarf (Std.)"
    )
    list_display = ("student", "state", "start", "display_demand")
    list_filter = ("state",)
    search_fields = ("student__first_name", "student__last_name", "notes")
    autocomplete_fields = ("student", "school")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student", "school")


@admin.register(School)
class SchoolAdmin(BaseModelAdmin):
    search_fields = ("school_name",)


@admin.register(PoolSchoolAgreement)
class PoolSchoolAgreementAdmin(BaseModelAdmin):
    list_display = ("payer", "flat_rate", "max_supervisions", "start", "end")
    list_filter = ("payer",)
    search_fields = ("payer__identifier",)
    autocomplete_fields = ("payer",)
    date_hierarchy = "start"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer")
