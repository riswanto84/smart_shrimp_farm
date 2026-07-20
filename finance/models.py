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

    class Meta:
        ordering = ['-date', '-id']


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
