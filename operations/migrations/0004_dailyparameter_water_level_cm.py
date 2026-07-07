# Generated manually for Smart Shrimp Farm
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0003_sampling_excel_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyparameter',
            name='water_level_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Tinggi Air (cm)'),
        ),
    ]
