from django.contrib import admin
from unfold.admin import ModelAdmin, GenericTabularInline
from .models import (
    Address,
    Phone,
    Email,
    BankAccount,
    Member,
    SchoolDays,
)
from .mixins import EditModeMixin, AdminDisplayMixin
from allauth.socialaccount.models import (
    SocialApp,
    SocialAccount,
    SocialToken,
    EmailAddress,
)

admin.site.unregister(SocialApp)
admin.site.unregister(SocialAccount)
admin.site.unregister(SocialToken)
admin.site.unregister(EmailAddress)


class ListSummaryMixin:
    """Mixin für ModelAdmin-Klassen mit generischer Zusammenfassungs-Footer-Karte.

    Subklassen implementieren get_summary_sections(cl) und geben eine Liste von
    Sektionen zurück. Jede Sektion ist eine Liste von {'label': str, 'value': str|int}-Dicts.
    Die Spaltenanzahl pro Sektion ergibt sich automatisch aus der Länge der Liste.
    """

    list_after_template = "admin/list_summary_footer.html"
    summary_title: str = "Zusammenfassung (aktuelle Filterung)"

    def get_summary_sections(self, cl) -> list[list[dict]]:
        return []

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            cl = response.context_data["cl"]
            response.context_data["summary_title"] = self.summary_title
            response.context_data["summary_sections"] = self.get_summary_sections(cl)
        except (AttributeError, KeyError):
            pass
        return response


class BaseModelAdmin(EditModeMixin, AdminDisplayMixin, ModelAdmin):
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in form.base_fields.values():
            if hasattr(field.widget, "can_delete_related"):
                field.widget.can_delete_related = False
        return form


class BaseGenericTabularInline(GenericTabularInline):
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        for field in formset.form.base_fields.values():
            if hasattr(field.widget, "can_delete_related"):
                field.widget.can_delete_related = False
        return formset


class AddressInline(BaseGenericTabularInline):
    model = Address
    extra = 0
    hide_title = True


class PhoneInline(BaseGenericTabularInline):
    model = Phone
    extra = 0
    hide_title = True


class EmailInline(BaseGenericTabularInline):
    model = Email
    extra = 0
    hide_title = True


class BankAccountInline(BaseGenericTabularInline):
    model = BankAccount
    extra = 0
    hide_title = True


@admin.register(SchoolDays)
class SchoolDaysAdmin(BaseModelAdmin):
    list_display = ("month", "school_days", "public_holidays", "vacation_days")
    search_fields = ("month",)


@admin.register(Member)
class MemberAdmin(BaseModelAdmin):
    list_display = ("full_name", "entrance_date", "membership_fee")
    search_fields = ("first_name", "last_name")
    inlines = [AddressInline, PhoneInline, EmailInline, BankAccountInline]
