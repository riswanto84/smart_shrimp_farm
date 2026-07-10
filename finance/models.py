from django.db import models
from ponds.models import Pond
from cultivation.models import CultivationCycle
class OperationalExpense(models.Model):
    cycle=models.ForeignKey(CultivationCycle,on_delete=models.PROTECT,null=True,blank=True,related_name='expenses')
    CATEGORIES=[('Pakan','Pakan'),('Listrik','Listrik'),('BBM','BBM'),('Obat & Probiotik','Obat & Probiotik'),('Tenaga Kerja','Tenaga Kerja'),('Peralatan','Peralatan'),('Perbaikan','Perbaikan'),('Transportasi','Transportasi'),('Lain-lain','Lain-lain')]
    date=models.DateField(); category=models.CharField(max_length=50, choices=CATEGORIES); pond=models.ForeignKey(Pond,on_delete=models.SET_NULL,null=True,blank=True)
    name=models.CharField(max_length=150); amount=models.DecimalField(max_digits=14, decimal_places=2); payment_method=models.CharField(max_length=30, default='Cash')
    receipt=models.ImageField(upload_to='receipts/', blank=True, null=True); notes=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
