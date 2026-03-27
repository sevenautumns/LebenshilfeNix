from django.contrib import admin
from unfold.admin import ModelAdmin, GenericTabularInline
from .models import (
    Address,
    Phone,
    Email,
    BankAccount,
    Denomination,
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


class PhoneInline(BaseGenericTabularInline):
    model = Phone
    extra = 0


class EmailInline(BaseGenericTabularInline):
    model = Email
    extra = 0


class BankAccountInline(BaseGenericTabularInline):
    model = BankAccount
    extra = 0


@admin.register(Denomination)
class DenominationAdmin(BaseModelAdmin):
    search_fields = ("name",)
