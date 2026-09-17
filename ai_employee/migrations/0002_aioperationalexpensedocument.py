from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('ai_employee', '0001_initial')]
    operations = [
        migrations.AlterField(
            model_name='aiaction', name='action',
            field=models.CharField(choices=[
                ('employee_advance.create', 'Buat Kasbon'),
                ('payroll.read', 'Baca Payroll'),
                ('employee.read', 'Baca Karyawan'),
                ('operational_expense.create', 'Buat Pengeluaran Operasional'),
            ], max_length=80),
        ),
        migrations.CreateModel(
            name='AIOperationalExpenseDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='ai_employee/operational_expenses/%Y/%m/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('content_type', models.CharField(blank=True, max_length=120)),
                ('file_size', models.PositiveBigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expense_documents', to='ai_employee.aiaction')),
            ],
            options={'ordering': ['created_at', 'id']},
        ),
    ]
