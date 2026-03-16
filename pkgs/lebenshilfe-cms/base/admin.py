from django.contrib import admin
from django.forms import NumberInput
from unfold.widgets import UnfoldPrefixSuffixMixin, INPUT_CLASSES
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import (
    Person, Address, Phone, Email, BankAccount, 
    CostPayerLink, MasterData, ExternalIdentifier, 
    Country, Denomination
)

class EuroDecimalWidget(UnfoldPrefixSuffixMixin, NumberInput):
    template_name = "unfold/widgets/text.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": " ".join(INPUT_CLASSES),
            "prefix_icon": "euro_symbol",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)        

class BaseModelAdmin(UnfoldModelAdmin):
    currency_fields = []

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in self.currency_fields:
            kwargs["widget"] = EuroDecimalWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in form.base_fields.values():
            if hasattr(field.widget, "can_delete_related"):
                field.widget.can_delete_related = False
        return form

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
