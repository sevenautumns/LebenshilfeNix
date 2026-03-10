from django.contrib import admin
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
    list_display = ('full_name', 'birthday', 'citizenship')
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
    list_display = ('employee', 'personnel_number', 'start_date', 'end_date', 'working_hours')
    search_fields = ('employee__first_name', 'employee__last_name', 'personnel_number')
    autocomplete_fields = ('employee',)
    list_filter = ('start_date', 'end_date')

@admin.register(Absence)
class AbsenceAdmin(BaseModelAdmin):
    list_display = ('employee', 'reason', 'start', 'end', 'certificate')
    list_filter = ('reason', 'certificate')
    autocomplete_fields = ('employee',)

@admin.register(TrainingRecord)
class TrainingRecordAdmin(BaseModelAdmin):
    list_display = ('staff', 'training_type', 'valid_from', 'valid_to')
    autocomplete_fields = ('staff', 'training_type')

@admin.register(TrainingType)
class TrainingTypeAdmin(BaseModelAdmin):
    search_fields = ('name',)

@admin.register(VocationalTraining)
class VocationalTrainingAdmin(BaseModelAdmin):
    search_fields = ('identifier',)

@admin.register(SalaryAgreement)
class SalaryAgreementAdmin(BaseModelAdmin):
    pass
