from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0003_alter_employee_base_salary_alter_employee_daily_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrecord',
            name='catatan',
            field=models.TextField(blank=True, verbose_name='Catatan'),
        ),
    ]
