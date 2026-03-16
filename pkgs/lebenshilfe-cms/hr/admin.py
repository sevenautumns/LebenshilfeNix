from django.contrib import admin
from django.utils import timezone
from django.db.models import Q
from base.admin import BaseModelAdmin, AddressInline, PhoneInline, EmailInline, BankAccountInline
from .models import (
    Employee, 
    Absence, 
    TrainingType, 
    VocationalTraining, 
    SalaryAgreement, 
    TrainingRecord, 
    Employment, 
    OtherEmployment
)

class OtherEmploymentInline(admin.TabularInline):
    model = OtherEmployment
    extra = 0

@admin.register(Employee)
class EmployeeAdmin(BaseModelAdmin):
    list_display = ('personnel_number', 'full_name', 'birthday', 'citizenship')
    search_fields = ('first_name', 'last_name') 
    filter_horizontal = ('vocational_trainings',)
    autocomplete_fields = ('country_of_birth', 'citizenship', 'church_membership')
    
    inlines = [
        OtherEmploymentInline, 
        AddressInline, 
        PhoneInline, 
        EmailInline, 
        BankAccountInline
    ]

@admin.register(Employment)
class EmploymentAdmin(BaseModelAdmin):
    list_display = ('employee', 'start_date', 'end_date', 'working_hours')
    search_fields = ('employee__first_name', 'employee__last_name', 'personnel_number')
    autocomplete_fields = ('employee',)
    list_filter = ('start_date', 'end_date')

@admin.register(Absence)
class AbsenceAdmin(BaseModelAdmin):
    list_display = ('employee', 'reason', 'start', 'end', 'certificate')
    list_filter = ('employee', 'reason', 'certificate')
    autocomplete_fields = ('employee',)

class TrainingValidityFilter(admin.SimpleListFilter):
    title = 'Gültig'
    parameter_name = 'is_valid'

    def lookups(self, request, model_admin):
        return (
            ('True', 'Ja'),
            ('False', 'Nein'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        val = self.value()
        
        if val == 'True':
            return queryset.filter(
                valid_from__lte=today
            ).filter(
                Q(valid_to__isnull=True) | Q(valid_to__gte=today)
            )

        if val == 'False':
            return queryset.filter(
                Q(valid_from__gt=today) | Q(valid_to__lt=today)
            )

        return queryset

@admin.register(TrainingRecord)
class TrainingRecordAdmin(BaseModelAdmin):
    list_display = ('staff', 'training_type', 'valid_from', 'valid_to', 'valid')
    autocomplete_fields = ('staff', 'training_type')
    list_filter = (TrainingValidityFilter, 'staff', 'training_type__name')

    @admin.display(description="Gültig", boolean=True, ordering='valid_to')
    def valid(self, obj):
        return obj.is_valid

@admin.register(TrainingType)
class TrainingTypeAdmin(BaseModelAdmin):
    search_fields = ('name',)

@admin.register(VocationalTraining)
class VocationalTrainingAdmin(BaseModelAdmin):
    list_display = ('name', 'qualified')
    list_filter = ('qualified',)
    search_fields = ('name',)

@admin.register(SalaryAgreement)
class SalaryAgreementAdmin(BaseModelAdmin):
    currency_fields = [
        "salary_standard",
        "salary_tandem",
        "salary_coordination",
        "salary_management",
    ]
