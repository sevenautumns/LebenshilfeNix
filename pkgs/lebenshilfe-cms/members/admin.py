from django.contrib import admin
from base.admin import BaseModelAdmin, AddressInline, PhoneInline, EmailInline, BankAccountInline
from .models import Member

@admin.register(Member)
class MemberAdmin(BaseModelAdmin):
    list_display = ('full_name', 'entrance_date', 'membership_fee')
    search_fields = ('first_name', 'last_name')
    inlines = [AddressInline, PhoneInline, EmailInline, BankAccountInline]
