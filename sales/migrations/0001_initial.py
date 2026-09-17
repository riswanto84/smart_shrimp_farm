from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [('operations','0001_initial'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='Customer', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('name', models.CharField(max_length=150)),('phone', models.CharField(blank=True, max_length=30)),('email', models.EmailField(blank=True, max_length=254)),('address', models.TextField(blank=True))]),
        migrations.CreateModel(name='Sale', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('invoice_no', models.CharField(max_length=50, unique=True)),('date', models.DateTimeField(auto_now_add=True)),('total_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),('payment_method', models.CharField(choices=[('Cash', 'Cash'), ('Transfer', 'Transfer'), ('Tempo', 'Tempo'), ('QRIS', 'QRIS')], default='Cash', max_length=20)),('status', models.CharField(choices=[('Lunas', 'Lunas'), ('Belum Lunas', 'Belum Lunas')], default='Lunas', max_length=20)),('notes', models.TextField(blank=True)),('cashier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='sales.customer'))]),
        migrations.CreateModel(name='SaleItem', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('size_text', models.CharField(help_text='Contoh: 50, 40-50, Campur', max_length=50)),('weight_kg', models.DecimalField(decimal_places=2, max_digits=10)),('price_per_kg', models.DecimalField(decimal_places=2, max_digits=14)),('subtotal', models.DecimalField(decimal_places=2, max_digits=14)),('harvest', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='operations.harvest')),('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='sales.sale'))]),
    ]
