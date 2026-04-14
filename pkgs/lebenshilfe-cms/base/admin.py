from django.contrib import admin
from unfold.admin import ModelAdmin, GenericTabularInline
from unfold.contrib.filters.admin import RangeDateFilter
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


class ReadOnlyAdminMixin:
    """Mixin für Modelle die nur als Leseansicht existieren (kein Hinzufügen, Ändern, Löschen)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
    list_display = (
        "full_name",
        "entrance_date",
        "leaving_date",
        "membership_fee",
        "authorization_id",
    )
    search_fields = ("first_name", "last_name")
    list_filter_submit = True
    list_filter = (
        ("entrance_date", RangeDateFilter),
        ("leaving_date", RangeDateFilter),
    )
    inlines = [AddressInline, PhoneInline, EmailInline, BankAccountInline]
