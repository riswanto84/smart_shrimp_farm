from django.db import models
from django.contrib.auth.models import User
from operations.models import Harvest
class Customer(models.Model):
    name=models.CharField(max_length=150); phone=models.CharField(max_length=30,blank=True); email=models.EmailField(blank=True); address=models.TextField(blank=True)
    def __str__(self): return self.name
class Sale(models.Model):
    PAYMENT=[('Cash','Cash'),('Transfer','Transfer'),('Tempo','Tempo'),('QRIS','QRIS')]
    STATUS=[('Lunas','Lunas'),('Belum Lunas','Belum Lunas')]
    invoice_no=models.CharField(max_length=50, unique=True)
    date=models.DateTimeField(auto_now_add=True)
    customer=models.ForeignKey(Customer,on_delete=models.SET_NULL,null=True,blank=True)
    total_kg=models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount=models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_method=models.CharField(max_length=20, choices=PAYMENT, default='Cash')
    status=models.CharField(max_length=20, choices=STATUS, default='Lunas')
    cashier=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    notes=models.TextField(blank=True)
class SaleItem(models.Model):
    sale=models.ForeignKey(Sale,on_delete=models.CASCADE, related_name='items')
    harvest=models.ForeignKey(Harvest,on_delete=models.SET_NULL,null=True,blank=True)
    size_text=models.CharField(max_length=50, help_text='Contoh: 50, 40-50, Campur')
    weight_kg=models.DecimalField(max_digits=10, decimal_places=2)
    price_per_kg=models.DecimalField(max_digits=14, decimal_places=2)
    subtotal=models.DecimalField(max_digits=14, decimal_places=2)
