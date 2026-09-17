from django.contrib import admin
from .models import EmployeeAdvance, EmployeeAdvanceRepayment, AIAction, AIAuditLog

@admin.register(EmployeeAdvance)
class EmployeeAdvanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'advance_date', 'amount', 'repaid_amount', 'status', 'created_by')
    list_filter = ('status', 'advance_date')
    search_fields = ('employee__name', 'employee__employee_code', 'purpose', 'document_number')

@admin.register(EmployeeAdvanceRepayment)
class EmployeeAdvanceRepaymentAdmin(admin.ModelAdmin):
    list_display = ('advance', 'repayment_date', 'amount', 'method', 'created_by')
    list_filter = ('method', 'repayment_date')

@admin.register(AIAction)
class AIActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'user', 'status', 'approved_by', 'created_at')
    list_filter = ('action', 'status')
    search_fields = ('command',)
    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'executed_at')

@admin.register(AIAuditLog)
class AIAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'event', 'actor', 'created_at')
    list_filter = ('event', 'created_at')
    readonly_fields = ('created_at',)
