from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ('finance', '0011_operationalexpense_capitalization')]
    operations = [
        migrations.CreateModel(name='Employee', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('employee_code', models.CharField(max_length=30, unique=True, verbose_name='NIK/Kode Karyawan')),
            ('name', models.CharField(max_length=150, verbose_name='Nama Karyawan')),
            ('position', models.CharField(max_length=100, verbose_name='Jabatan')),
            ('phone', models.CharField(blank=True, max_length=30, verbose_name='Nomor Telepon')),
            ('bank_name', models.CharField(blank=True, max_length=80, verbose_name='Bank')),
            ('bank_account', models.CharField(blank=True, max_length=80, verbose_name='Nomor Rekening')),
            ('join_date', models.DateField(default=django.utils.timezone.localdate, verbose_name='Tanggal Masuk')),
            ('employment_status', models.CharField(choices=[('active','Aktif'),('inactive','Tidak Aktif'),('resigned','Berhenti')], default='active', max_length=20, verbose_name='Status Karyawan')),
            ('pay_type', models.CharField(choices=[('monthly','Bulanan'),('daily','Harian')], default='monthly', max_length=20, verbose_name='Jenis Gaji')),
            ('base_salary', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Gaji Pokok')),
            ('daily_rate', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Upah Harian')),
            ('notes', models.TextField(blank=True, verbose_name='Catatan')),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
        ], options={'ordering':['name']}),
        migrations.CreateModel(name='PayrollPeriod', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=100, verbose_name='Nama Periode')),
            ('start_date', models.DateField(verbose_name='Tanggal Mulai')), ('end_date', models.DateField(verbose_name='Tanggal Selesai')),
            ('payment_date', models.DateField(blank=True, null=True, verbose_name='Tanggal Pembayaran')),
            ('status', models.CharField(choices=[('draft','Draft'),('processed','Diproses'),('closed','Ditutup')], default='draft', max_length=20, verbose_name='Status')),
            ('notes', models.TextField(blank=True, verbose_name='Catatan')), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
        ], options={'ordering':['-start_date','-id']}),
        migrations.CreateModel(name='PayrollRecord', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('work_days', models.DecimalField(decimal_places=2, default=0, max_digits=6, verbose_name='Hari Kerja')),
            ('base_salary', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Gaji Pokok/Upah')),
            ('overtime_pay', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Lembur')),
            ('meal_allowance', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Uang Makan')),
            ('transport_allowance', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Transportasi')),
            ('other_allowance', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Tunjangan Lain')),
            ('bonus', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Bonus')),
            ('bpjs_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Potongan BPJS')),
            ('tax_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Potongan Pajak')),
            ('loan_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Potongan Kasbon')),
            ('other_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Potongan Lain')),
            ('gross_salary', models.DecimalField(decimal_places=2, default=0, max_digits=16)), ('total_deduction', models.DecimalField(decimal_places=2, default=0, max_digits=16)), ('net_salary', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
            ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name='Jumlah Dibayar')),
            ('payment_status', models.CharField(choices=[('unpaid','Belum Dibayar'),('partial','Dibayar Sebagian'),('paid','Lunas')], default='unpaid', max_length=20, verbose_name='Status Pembayaran')),
            ('payment_method', models.CharField(choices=[('Transfer','Transfer'),('Cash','Tunai'),('Lainnya','Lainnya')], default='Transfer', max_length=30, verbose_name='Metode Pembayaran')),
            ('payment_date', models.DateField(blank=True, null=True, verbose_name='Tanggal Pembayaran')), ('notes', models.TextField(blank=True, verbose_name='Catatan')),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payroll_records', to='payroll.employee')),
            ('expense', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payroll_record', to='finance.operationalexpense')),
            ('period', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='payroll.payrollperiod')),
        ], options={'ordering':['employee__name']}),
        migrations.AddConstraint(model_name='payrollrecord', constraint=models.UniqueConstraint(fields=('period','employee'), name='unique_employee_payroll_period')),
    ]
