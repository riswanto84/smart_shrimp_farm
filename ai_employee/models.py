from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class EmployeeAdvance(models.Model):
    STATUS = [
        ('outstanding', 'Berjalan'),
        ('partially_paid', 'Sebagian Dibayar'),
        ('settled', 'Lunas'),
        ('cancelled', 'Dibatalkan'),
    ]
    employee = models.ForeignKey('payroll.Employee', on_delete=models.PROTECT, related_name='advances')
    advance_date = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    repaid_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))])
    purpose = models.CharField(max_length=255, blank=True)
    document_number = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='outstanding', db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_employee_advances')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-advance_date', '-id']
        indexes = [models.Index(fields=['employee', 'status']), models.Index(fields=['advance_date'])]

    @property
    def outstanding_amount(self):
        return max((self.amount or Decimal('0')) - (self.repaid_amount or Decimal('0')), Decimal('0'))

    def refresh_status(self, save=True):
        if self.status == 'cancelled':
            return
        outstanding = self.outstanding_amount
        self.status = 'settled' if outstanding <= 0 else ('partially_paid' if self.repaid_amount > 0 else 'outstanding')
        if save:
            self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f'{self.employee.name} - Rp{self.amount:,.0f}'


class EmployeeAdvanceRepayment(models.Model):
    advance = models.ForeignKey(EmployeeAdvance, on_delete=models.CASCADE, related_name='repayments')
    repayment_date = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    method = models.CharField(max_length=30, default='Payroll')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-repayment_date', '-id']

    def __str__(self):
        return f'{self.advance.employee.name} - Rp{self.amount:,.0f}'


class AIAction(models.Model):
    STATUS = [
        ('draft', 'Menunggu Persetujuan'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
        ('executed', 'Berhasil'),
        ('failed', 'Gagal'),
    ]
    ACTIONS = [
        ('employee_advance.create', 'Buat Kasbon'),
        ('payroll.read', 'Baca Payroll'),
        ('employee.read', 'Baca Karyawan'),
        ('operational_expense.create', 'Buat Pengeluaran Operasional'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_actions')
    action = models.CharField(max_length=80, choices=ACTIONS)
    command = models.TextField()
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='draft', db_index=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_ai_actions')
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['status', 'created_at']), models.Index(fields=['action', 'status'])]

    def __str__(self):
        return f'{self.action} #{self.pk} ({self.status})'


class AIAuditLog(models.Model):
    action = models.ForeignKey(AIAction, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_audit_logs')
    event = models.CharField(max_length=80)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.event} - AIAction #{self.action_id}'


class AIOperationalExpenseDocument(models.Model):
    """Bukti yang diunggah untuk draft AI OperationalExpense."""
    action = models.ForeignKey(AIAction, on_delete=models.CASCADE, related_name='expense_documents')
    file = models.FileField(upload_to='ai_employee/operational_expenses/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return self.original_name or self.file.name
