from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator
import decimal

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payroll', '0004_payrollrecord_catatan'),
    ]
    operations = [
        migrations.CreateModel(
            name='AIAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('employee_advance.create','Buat Kasbon'),('payroll.read','Baca Payroll'),('employee.read','Baca Karyawan')], max_length=80)),
                ('command', models.TextField()),
                ('payload', models.JSONField(default=dict)),
                ('result', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('draft','Menunggu Persetujuan'),('approved','Disetujui'),('rejected','Ditolak'),('executed','Berhasil'),('failed','Gagal')], db_index=True, default='draft', max_length=20)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('executed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_ai_actions', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_actions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-created_at','-id']},
        ),
        migrations.CreateModel(
            name='EmployeeAdvance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('advance_date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=16, validators=[MinValueValidator(decimal.Decimal('0.01'))])),
                ('repaid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=16, validators=[MinValueValidator(decimal.Decimal('0'))])),
                ('purpose', models.CharField(blank=True, max_length=255)),
                ('document_number', models.CharField(blank=True, max_length=80)),
                ('notes', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('outstanding','Berjalan'),('partially_paid','Sebagian Dibayar'),('settled','Lunas'),('cancelled','Dibatalkan')], db_index=True, default='outstanding', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_employee_advances', to=settings.AUTH_USER_MODEL)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='advances', to='payroll.employee')),
            ],
            options={'ordering':['-advance_date','-id']},
        ),
        migrations.CreateModel(
            name='EmployeeAdvanceRepayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('repayment_date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=16, validators=[MinValueValidator(decimal.Decimal('0.01'))])),
                ('method', models.CharField(default='Payroll', max_length=30)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('advance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repayments', to='ai_employee.employeeadvance')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-repayment_date','-id']},
        ),
        migrations.CreateModel(
            name='AIAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(max_length=80)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='ai_employee.aiaction')),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-created_at','-id']},
        ),
        migrations.AddIndex(model_name='aiaction', index=models.Index(fields=['status','created_at'], name='ai_employee_ai_status_6c1e5a_idx')),
        migrations.AddIndex(model_name='aiaction', index=models.Index(fields=['action','status'], name='ai_employee_ai_action_2e1f9f_idx')),
        migrations.AddIndex(model_name='employeeadvance', index=models.Index(fields=['employee','status'], name='ai_employee_employe_3b3f5a_idx')),
        migrations.AddIndex(model_name='employeeadvance', index=models.Index(fields=['advance_date'], name='ai_employee_advanc_0f2f5c_idx')),
    ]
