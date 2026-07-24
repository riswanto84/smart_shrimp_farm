from decimal import Decimal
from django.db import models
from ponds.models import Pond
from cultivation.models import CultivationCycle


class OperationalExpense(models.Model):
    cycle=models.ForeignKey(CultivationCycle,on_delete=models.PROTECT,null=True,blank=True,related_name='expenses')
    CATEGORIES=[('Benur','Benur'),('Pakan','Pakan'),('Listrik','Listrik'),('BBM','BBM'),('Obat & Probiotik','Obat & Probiotik'),('Tenaga Kerja','Tenaga Kerja'),('Jasa Pengelola','Jasa Pengelola'),('Peralatan','Peralatan'),('Perbaikan','Perbaikan'),('Transportasi','Transportasi'),('Panen','Panen'),('Administrasi','Administrasi'),('Penyusutan','Penyusutan'),('Pajak','Pajak'),('Lain-lain','Lain-lain')]
    date=models.DateField(); category=models.CharField(max_length=50, choices=CATEGORIES); pond=models.ForeignKey(Pond,on_delete=models.SET_NULL,null=True,blank=True)
    name=models.CharField(max_length=150); amount=models.DecimalField(max_digits=16, decimal_places=2); payment_method=models.CharField(max_length=30, default='Cash')
    receipt=models.ImageField(upload_to='receipts/', blank=True, null=True); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
    is_fiscal_deductible=models.BooleanField(default=True, verbose_name='Dapat dikurangkan secara fiskal')
    document_number=models.CharField(max_length=80, blank=True, verbose_name='Nomor bukti')
    is_capital_expenditure=models.BooleanField(default=False, verbose_name='Pembelian aset/kapitalisasi')
    fixed_asset=models.ForeignKey('FixedAsset', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_expenses', verbose_name='Aset terkait')

    class Meta:
        ordering = ['-date', '-id']


class ExpenseDocument(models.Model):
    expense = models.ForeignKey(OperationalExpense, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='finance/expense_documents/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=180, blank=True)
    uploaded_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='uploaded_expense_documents'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at', '-id']

    def __str__(self):
        return self.original_name or self.file.name

    @property
    def file_extension(self):
        from pathlib import Path
        return Path(self.original_name or self.file.name).suffix.lower().lstrip('.')


class OtherRevenue(models.Model):
    cycle=models.ForeignKey(CultivationCycle,on_delete=models.PROTECT,null=True,blank=True,related_name='other_revenues')
    date=models.DateField()
    document_number=models.CharField(max_length=80, blank=True)
    REVENUE_TYPES=[('Penjualan hasil sampingan','Penjualan hasil sampingan'),('Jasa','Jasa'),('Pendapatan lain-lain','Pendapatan lain-lain')]
    revenue_type=models.CharField(max_length=60,choices=REVENUE_TYPES,default='Pendapatan lain-lain')
    description=models.CharField(max_length=180)
    customer=models.CharField(max_length=150,blank=True)
    gross_amount=models.DecimalField(max_digits=16,decimal_places=2)
    tax_amount=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    payment_method=models.CharField(max_length=30,default='Transfer')
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['-date','-id']


class BalanceEntry(models.Model):
    ASSET='asset'; LIABILITY='liability'; EQUITY='equity'
    ACCOUNT_TYPES=[(ASSET,'Aset'),(LIABILITY,'Kewajiban'),(EQUITY,'Ekuitas')]
    ASSET_GROUPS=[('Kas dan Bank','Kas dan Bank'),('Piutang Usaha','Piutang Usaha'),('Persediaan','Persediaan'),('Uang Muka','Uang Muka'),('Aset Lancar Lainnya','Aset Lancar Lainnya'),('Aset Tetap','Aset Tetap')]
    LIABILITY_GROUPS=[('Utang Usaha','Utang Usaha'),('Utang Pajak','Utang Pajak'),('Utang Pemilik','Utang Pemilik'),('Utang Lainnya','Utang Lainnya')]
    EQUITY_GROUPS=[('Modal Pemilik','Modal Pemilik'),('Tambahan Modal','Tambahan Modal'),('Prive','Prive'),('Laba Ditahan','Laba Ditahan')]
    as_of_date=models.DateField(verbose_name='Tanggal posisi')
    account_type=models.CharField(max_length=20,choices=ACCOUNT_TYPES)
    group=models.CharField(max_length=60)
    account_name=models.CharField(max_length=150)
    amount=models.DecimalField(max_digits=16,decimal_places=2)
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['account_type','group','account_name']


class FixedAsset(models.Model):
    STATUS=[('active','Aktif'),('sold','Dijual'),('damaged','Rusak'),('disposed','Dihapuskan')]
    METHODS=[('straight_line','Garis Lurus')]
    FISCAL_GROUPS=[('non_depreciable','Tidak disusutkan'),('group_1','Kelompok 1'),('group_2','Kelompok 2'),('group_3','Kelompok 3'),('group_4','Kelompok 4'),('permanent_building','Bangunan Permanen'),('non_permanent_building','Bangunan Tidak Permanen')]
    code=models.CharField(max_length=40,unique=True)
    name=models.CharField(max_length=180)
    category=models.CharField(max_length=100)
    acquisition_date=models.DateField()
    use_date=models.DateField()
    acquisition_cost=models.DecimalField(max_digits=16,decimal_places=2)
    additional_cost=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    residual_value=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    commercial_useful_life_years=models.PositiveSmallIntegerField(default=4)
    fiscal_group=models.CharField(max_length=40,choices=FISCAL_GROUPS,default='group_1')
    method=models.CharField(max_length=30,choices=METHODS,default='straight_line')
    location=models.CharField(max_length=150,blank=True)
    document_number=models.CharField(max_length=80,blank=True)
    source_of_funds=models.CharField(max_length=100,blank=True)
    status=models.CharField(max_length=20,choices=STATUS,default='active')
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['code']

    @property
    def total_cost(self):
        return (self.acquisition_cost or Decimal('0')) + (self.additional_cost or Decimal('0'))

class TradeAccount(models.Model):
    RECEIVABLE = 'receivable'
    PAYABLE = 'payable'
    ACCOUNT_TYPES = [
        (RECEIVABLE, 'Piutang Usaha'),
        (PAYABLE, 'Utang Usaha'),
    ]

    cycle = models.ForeignKey(
        CultivationCycle, on_delete=models.PROTECT, null=True, blank=True,
        related_name='trade_accounts'
    )
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    transaction_date = models.DateField(verbose_name='Tanggal transaksi')
    due_date = models.DateField(verbose_name='Tanggal jatuh tempo')
    document_number = models.CharField(max_length=80, blank=True, verbose_name='Nomor dokumen')
    customer = models.ForeignKey(
        'sales.Customer', on_delete=models.PROTECT, null=True, blank=True,
        related_name='receivables', verbose_name='Pelanggan'
    )
    partner_name = models.CharField(max_length=180, verbose_name='Pelanggan/Supplier')
    description = models.CharField(max_length=220)
    original_amount = models.DecimalField(max_digits=16, decimal_places=2, verbose_name='Nilai awal')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'transaction_date', 'id']
        indexes = [
            models.Index(fields=['account_type', 'due_date']),
            models.Index(fields=['partner_name']),
        ]

    def __str__(self):
        return f"{self.get_account_type_display()} - {self.partner_name} - {self.document_number or self.pk}"

    @property
    def paid_amount(self):
        return self.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    @property
    def outstanding_amount(self):
        return max((self.original_amount or Decimal('0')) - self.paid_amount, Decimal('0'))

    @property
    def payment_status(self):
        if self.outstanding_amount <= 0:
            return 'Lunas'
        if self.paid_amount > 0:
            return 'Sebagian'
        return 'Belum Dibayar'

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.outstanding_amount > 0 and self.due_date < timezone.localdate()


class TradePayment(models.Model):
    METHODS = [
        ('Transfer', 'Transfer'),
        ('Cash', 'Tunai'),
        ('Giro', 'Giro'),
        ('Lainnya', 'Lainnya'),
    ]
    trade_account = models.ForeignKey(TradeAccount, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField(verbose_name='Tanggal pembayaran')
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=METHODS, default='Transfer')
    document_number = models.CharField(max_length=80, blank=True, verbose_name='Nomor bukti')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['payment_date', 'id']

    def __str__(self):
        return f"{self.trade_account} - {self.amount}"


class TradeDocument(models.Model):
    trade_account = models.ForeignKey(TradeAccount, on_delete=models.CASCADE, related_name='documents')
    payment = models.ForeignKey(TradePayment, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    file = models.FileField(upload_to='finance/trade_documents/%Y/%m/')
    original_name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=180, blank=True)
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_trade_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at', '-id']

    def __str__(self):
        return self.original_name or self.file.name

    @property
    def file_extension(self):
        from pathlib import Path
        return Path(self.original_name or self.file.name).suffix.lower().lstrip('.')


class LedgerAccount(models.Model):
    ASSET = 'asset'
    LIABILITY = 'liability'
    EQUITY = 'equity'
    REVENUE = 'revenue'
    EXPENSE = 'expense'
    ACCOUNT_TYPES = [
        (ASSET, 'Aset'),
        (LIABILITY, 'Kewajiban'),
        (EQUITY, 'Ekuitas'),
        (REVENUE, 'Pendapatan'),
        (EXPENSE, 'Beban'),
    ]
    NORMAL_DEBIT = 'debit'
    NORMAL_CREDIT = 'credit'
    NORMAL_BALANCES = [
        (NORMAL_DEBIT, 'Debit'),
        (NORMAL_CREDIT, 'Kredit'),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    normal_balance = models.CharField(max_length=10, choices=NORMAL_BALANCES)
    group = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class JournalEntry(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_POSTED = 'posted'
    STATUS_VOID = 'void'
    STATUSES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_POSTED, 'Diposting'),
        (STATUS_VOID, 'Dibatalkan'),
    ]

    date = models.DateField(db_index=True)
    reference = models.CharField(max_length=100, blank=True, db_index=True)
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUSES, default=STATUS_POSTED)
    source_type = models.CharField(max_length=50, blank=True, db_index=True)
    source_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    is_system_generated = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='finance_journal_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['source_type', 'source_id'],
                condition=models.Q(is_system_generated=True),
                name='uniq_system_journal_source'
            )
        ]

    def __str__(self):
        return self.reference or f'Jurnal #{self.pk}'

    @property
    def total_debit(self):
        return self.lines.aggregate(total=models.Sum('debit'))['total'] or Decimal('0')

    @property
    def total_credit(self):
        return self.lines.aggregate(total=models.Sum('credit'))['total'] or Decimal('0')

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(LedgerAccount, on_delete=models.PROTECT, related_name='journal_lines')
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        ordering = ['entry_id', 'id']

    def __str__(self):
        return f'{self.entry} - {self.account}'

    def clean(self):
        from django.core.exceptions import ValidationError
        debit = self.debit or Decimal('0')
        credit = self.credit or Decimal('0')
        if debit < 0 or credit < 0:
            raise ValidationError('Debit dan kredit tidak boleh negatif.')
        if bool(debit) == bool(credit):
            raise ValidationError('Satu baris harus berisi debit atau kredit, bukan keduanya.')
