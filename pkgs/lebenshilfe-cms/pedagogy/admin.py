from django.contrib import admin
from base.admin import BaseModelAdmin, AddressInline, PhoneInline, EmailInline
from .models import School, Student, Supervision, Request

@admin.register(Student)
class StudentAdmin(BaseModelAdmin):
    list_display = ('full_name', 'payer')
    search_fields = ('first_name', 'last_name')
    inlines = [AddressInline, PhoneInline, EmailInline]
    autocomplete_fields = ('payer',)

@admin.register(Supervision)
class SupervisionAdmin(BaseModelAdmin):
    list_display = ('student', 'caretaker', 'school', 'start', 'end')
    list_filter = ('school', 'start')
    search_fields = ('student', 'start')
    autocomplete_fields = ('student', 'tandem', 'caretaker', 'school')

@admin.register(Request)
class RequestAdmin(BaseModelAdmin):
    list_display = ('student', 'state', 'start', 'demand')
    list_filter = ('state',)
    autocomplete_fields = ('student', 'school')

@admin.register(School)
class SchoolAdmin(BaseModelAdmin):
    search_fields = ('school_name',)
