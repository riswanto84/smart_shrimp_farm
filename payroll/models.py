from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Employee(models.Model):
    EMPLOYMENT_STATUS = [
        ('active', 'Aktif'),
        ('inactive', 'Tidak Aktif'),
        ('resigned', 'Berhenti'),
    ]
    PAY_TYPE = [
        ('monthly', 'Bulanan'),
        ('daily', 'Harian'),
    ]

    employee_code = models.CharField(max_length=30, unique=True, verbose_name='NIK/Kode Karyawan')
    name = models.CharField(max_length=150, verbose_name='Nama Karyawan')
    position = models.CharField(max_length=100, verbose_name='Jabatan')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Nomor Telepon')
    bank_name = models.CharField(max_length=80, blank=True, verbose_name='Bank')
    bank_account = models.CharField(max_length=80, blank=True, verbose_name='Nomor Rekening')
    join_date = models.DateField(default=timezone.localdate, verbose_name='Tanggal Masuk')
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, default='active', verbose_name='Status Karyawan')
    pay_type = models.CharField(max_length=20, choices=PAY_TYPE, default='monthly', verbose_name='Jenis Gaji')
    base_salary = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Gaji Pokok')
    daily_rate = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Upah Harian')
    notes = models.TextField(blank=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.employee_code} - {self.name}'


class PayrollPeriod(models.Model):
    STATUS = [
        ('draft', 'Draft'),
        ('processed', 'Diproses'),
        ('closed', 'Ditutup'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nama Periode')
    start_date = models.DateField(verbose_name='Tanggal Mulai')
    end_date = models.DateField(verbose_name='Tanggal Selesai')
    payment_date = models.DateField(null=True, blank=True, verbose_name='Tanggal Pembayaran')
    status = models.CharField(max_length=20, choices=STATUS, default='draft', verbose_name='Status')
    notes = models.TextField(blank=True, verbose_name='Catatan')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-id']

    def __str__(self):
        return self.name

    @property
    def total_gross(self):
        return self.records.aggregate(v=models.Sum('gross_salary'))['v'] or Decimal('0')

    @property
    def total_deductions(self):
        return self.records.aggregate(v=models.Sum('total_deduction'))['v'] or Decimal('0')

    @property
    def total_net(self):
        return self.records.aggregate(v=models.Sum('net_salary'))['v'] or Decimal('0')


class PayrollRecord(models.Model):
    PAYMENT_STATUS = [
        ('unpaid', 'Belum Dibayar'),
        ('partial', 'Dibayar Sebagian'),
        ('paid', 'Lunas'),
    ]
    PAYMENT_METHODS = [
        ('Transfer', 'Transfer'),
        ('Cash', 'Tunai'),
        ('Lainnya', 'Lainnya'),
    ]

    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name='records')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='payroll_records')
    work_days = models.DecimalField(max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Hari Kerja')
    base_salary = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Gaji Pokok/Upah')
    overtime_pay = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Lembur')
    meal_allowance = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Uang Makan')
    transport_allowance = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Transportasi')
    other_allowance = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Tunjangan Lain')
    bonus = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Bonus')
    bpjs_deduction = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Potongan BPJS')
    tax_deduction = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Potongan Pajak')
    loan_deduction = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Potongan Kasbon')
    other_deduction = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Potongan Lain')
    gross_salary = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_deduction = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))], verbose_name='Jumlah Dibayar')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='unpaid', verbose_name='Status Pembayaran')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='Transfer', verbose_name='Metode Pembayaran')
    payment_date = models.DateField(null=True, blank=True, verbose_name='Tanggal Pembayaran')
    notes = models.TextField(blank=True, verbose_name='Keterangan')
    catatan = models.TextField(blank=True, verbose_name='Catatan')
    expense = models.OneToOneField('finance.OperationalExpense', on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_record')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee__name']
        constraints = [models.UniqueConstraint(fields=['period', 'employee'], name='unique_employee_payroll_period')]

    def __str__(self):
        return f'{self.period} - {self.employee.name}'

    @property
    def outstanding_amount(self):
        return max((self.net_salary or Decimal('0')) - (self.amount_paid or Decimal('0')), Decimal('0'))

    def calculate(self):
        self.gross_salary = sum([
            self.base_salary or Decimal('0'), self.overtime_pay or Decimal('0'),
            self.meal_allowance or Decimal('0'), self.transport_allowance or Decimal('0'),
            self.other_allowance or Decimal('0'), self.bonus or Decimal('0')
        ], Decimal('0'))
        self.total_deduction = sum([
            self.bpjs_deduction or Decimal('0'), self.tax_deduction or Decimal('0'),
            self.loan_deduction or Decimal('0'), self.other_deduction or Decimal('0')
        ], Decimal('0'))
        self.net_salary = max(self.gross_salary - self.total_deduction, Decimal('0'))
        if self.amount_paid <= 0:
            self.payment_status = 'unpaid'
        elif self.amount_paid < self.net_salary:
            self.payment_status = 'partial'
        else:
            self.amount_paid = self.net_salary
            self.payment_status = 'paid'

    def save(self, *args, **kwargs):
        self.calculate()
        super().save(*args, **kwargs)
