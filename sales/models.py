from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from operations.models import Harvest
from cultivation.models import CultivationCycle


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Sale(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='sales')
    PAYMENT = [('Cash', 'Cash'), ('Transfer', 'Transfer'), ('Tempo', 'Tempo'), ('QRIS', 'QRIS'), ('Midtrans', 'Midtrans')]
    STATUS = [
        ('Lunas', 'Lunas'),
        ('Belum Lunas', 'Belum Lunas'),
        ('Menunggu Pembayaran', 'Menunggu Pembayaran'),
        ('Gagal', 'Gagal'),
        ('Expired', 'Expired'),
        ('Dibatalkan', 'Dibatalkan'),
        ('Refund', 'Refund'),
    ]

    invoice_no = models.CharField(max_length=50, unique=True)
    date = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    total_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Total akhir nota = subtotal item + biaya opsional.
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Ongkos kirim')
    packing_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Biaya pengepakan')
    other_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Biaya lainnya')

    payment_method = models.CharField(max_length=20, choices=PAYMENT, default='Cash')
    status = models.CharField(max_length=20, choices=STATUS, default='Lunas')
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Integrasi Midtrans Snap / webhook.
    midtrans_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    midtrans_transaction_id = models.CharField(max_length=100, blank=True)
    midtrans_snap_token = models.CharField(max_length=255, blank=True)
    midtrans_payment_url = models.URLField(blank=True)
    midtrans_payment_type = models.CharField(max_length=50, blank=True)
    midtrans_status = models.CharField(max_length=50, blank=True)
    midtrans_raw_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    @property
    def items_subtotal(self):
        total = Decimal('0')
        for item in self.items.all():
            total += item.subtotal or Decimal('0')
        return total

    @property
    def extra_cost_total(self):
        return (self.shipping_cost or Decimal('0')) + (self.packing_cost or Decimal('0')) + (self.other_cost or Decimal('0'))


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    harvest = models.ForeignKey(Harvest, on_delete=models.SET_NULL, null=True, blank=True)
    size_text = models.CharField(max_length=50, help_text='Contoh: 50, 40-50, Campur')
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=14, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
