from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('sales','0006_backfill_legacy_cycle_data'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AlterField(model_name='sale', name='payment_method', field=models.CharField(choices=[('Cash','Cash'),('Transfer','Transfer'),('Tempo','Tempo'),('QRIS','QRIS'),('Midtrans','Midtrans'),('Campuran','Pembayaran Campuran'),('Lainnya','Metode Lainnya')], default='Cash', max_length=20)),
        migrations.AddField(model_name='sale', name='cash_amount', field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name='sale', name='transfer_amount', field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name='sale', name='qris_amount', field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name='sale', name='other_payment_amount', field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name='sale', name='other_payment_method', field=models.CharField(blank=True, max_length=100)),
        migrations.CreateModel(name='SaleDocument', fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('document_type',models.CharField(choices=[('Bukti Transfer','Bukti Transfer'),('Tanda Terima','Tanda Terima'),('Kwitansi','Kwitansi'),('Invoice','Invoice'),('Surat Jalan','Surat Jalan'),('Faktur Pajak','Faktur Pajak'),('Lainnya','Dokumen Lainnya')],default='Bukti Transfer',max_length=30)),('file',models.FileField(upload_to='sales/documents/%Y/%m/')),('description',models.CharField(blank=True,max_length=255)),('uploaded_at',models.DateTimeField(auto_now_add=True)),('sale',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='documents',to='sales.sale')),('uploaded_by',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL))]),
    ]
