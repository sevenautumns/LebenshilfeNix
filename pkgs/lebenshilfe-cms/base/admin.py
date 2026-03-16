from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import (
    Person, Address, Phone, Email, BankAccount, 
    CostPayerLink, MasterData, ExternalIdentifier, 
    Country, Denomination
)
from .widgets import *

class BaseModelAdmin(UnfoldModelAdmin):
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

class AddressInline(GenericTabularInline):
    model = Address
    extra = 0

class PhoneInline(GenericTabularInline):
    model = Phone
    extra = 0

class EmailInline(GenericTabularInline):
    model = Email
    extra = 0

class BankAccountInline(GenericTabularInline):
    model = BankAccount
    extra = 0

class ExternalIdentifierInline(GenericTabularInline):
    model = ExternalIdentifier
    extra = 0
    verbose_name = "Identifikator"
    verbose_name_plural = "Identifikatoren"

class CostPayerLinkInline(GenericTabularInline):
    model = CostPayerLink
    extra = 0
    autocomplete_fields = ('identifier',)

@admin.register(Country)
class CountryAdmin(BaseModelAdmin):
    search_fields = ('name',)

@admin.register(Denomination)
class DenominationAdmin(BaseModelAdmin):
    search_fields = ('name',)

@admin.register(MasterData)
class MasterDataAdmin(BaseModelAdmin):
    inlines = [ExternalIdentifierInline, BankAccountInline]
