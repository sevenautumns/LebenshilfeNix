from typing import Union
from django.contrib import admin
from django.http import HttpRequest 
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin, GenericTabularInline
from unfold.decorators import action
from unfold.enums import ActionVariant
from .models import (
    Person, Address, Phone, Email, BankAccount, 
    CostPayerLink, MasterData, ExternalIdentifier, 
    Denomination
)
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken, EmailAddress
from .widgets import *

admin.site.unregister(SocialApp)
admin.site.unregister(SocialAccount)
admin.site.unregister(SocialToken)
admin.site.unregister(EmailAddress)

class EditModeMixin:
    actions_detail = ["edit_action"]

    def _get_change_url(self, object_id: int) -> str:
        return reverse(
            f"admin:{self.opts.app_label}_{self.opts.model_name}_change", 
            args=[object_id]
        )

    @action(
        description="Bearbeiten",
        url_path="edit-action",
        permissions=["edit_action"],
        variant=ActionVariant.PRIMARY,
    )
    def edit_action(self, request: HttpRequest, object_id: int):
        url = self._get_change_url(object_id)
        return redirect(f"{url}?edit=1")

    def has_edit_action_permission(self, request, obj=None):
        return not self.is_edit(request)

    def is_edit(self, request):
        return request.GET.get('edit') == '1'

    def has_change_permission(self, request, obj=None):
        has_class_permission = super().has_change_permission(request, obj)
        if not has_class_permission:
            return False
        return self.is_edit(request)
    
class BaseModelAdmin(EditModeMixin, ModelAdmin):
    hour_minute_fields = []
    currency_fields = []

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in self.currency_fields:
            kwargs["widget"] = EuroDecimalWidget
        if db_field.name in self.hour_minute_fields:
            kwargs["widget"] = HourMinuteDurationWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in form.base_fields.values():
            if hasattr(field.widget, "can_delete_related"):
                field.widget.can_delete_related = False
        return form

    @staticmethod
    def duration_display(field_name, description="Dauer"):
        @admin.display(description=description, ordering=field_name)
        def display_fn(self, obj):
            value = getattr(obj, field_name)
            if value:
                total_seconds = int(value.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}:{minutes:02d} Std."
            return "-"
        return display_fn

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

class ExternalIdentifierInline(BaseGenericTabularInline):
    model = ExternalIdentifier
    extra = 0
    verbose_name = "Identifikator"
    verbose_name_plural = "Identifikatoren"

class CostPayerLinkInline(BaseGenericTabularInline):
    model = CostPayerLink
    extra = 0
    autocomplete_fields = ('identifier',)

@admin.register(Denomination)
class DenominationAdmin(BaseModelAdmin):
    search_fields = ('name',)

@admin.register(MasterData)
class MasterDataAdmin(BaseModelAdmin):
    inlines = [ExternalIdentifierInline, BankAccountInline]
