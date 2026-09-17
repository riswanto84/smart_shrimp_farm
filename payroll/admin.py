from django.contrib import admin
from .models import Employee, PayrollPeriod, PayrollRecord

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'name', 'position', 'employment_status', 'pay_type', 'base_salary')
    search_fields = ('employee_code', 'name', 'position')
    list_filter = ('employment_status', 'pay_type')

class PayrollRecordInline(admin.TabularInline):
    model = PayrollRecord
    extra = 0

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'status')
    inlines = [PayrollRecordInline]

@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ('period', 'employee', 'gross_salary', 'total_deduction', 'net_salary', 'payment_status')
    list_filter = ('payment_status', 'period')
