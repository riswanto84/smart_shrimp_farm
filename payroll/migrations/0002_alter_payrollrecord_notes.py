from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payrollrecord',
            name='notes',
            field=models.TextField(blank=True, verbose_name='Keterangan'),
        ),
    ]
