from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [('ponds','0001_initial')]
    operations = [
        migrations.CreateModel(name='OperationalExpense', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('date', models.DateField()),('category', models.CharField(choices=[('Pakan','Pakan'),('Listrik','Listrik'),('BBM','BBM'),('Obat & Probiotik','Obat & Probiotik'),('Tenaga Kerja','Tenaga Kerja'),('Peralatan','Peralatan'),('Perbaikan','Perbaikan'),('Transportasi','Transportasi'),('Lain-lain','Lain-lain')], max_length=50)),('name', models.CharField(max_length=150)),('amount', models.DecimalField(decimal_places=2, max_digits=14)),('payment_method', models.CharField(default='Cash', max_length=30)),('receipt', models.ImageField(blank=True, null=True, upload_to='receipts/')),('notes', models.TextField(blank=True)),('created_at', models.DateTimeField(auto_now_add=True)),('pond', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='ponds.pond'))]),
    ]
