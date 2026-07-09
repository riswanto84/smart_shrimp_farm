# Generated manually for Smart Shrimp Farm parameter pagi/sore fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0005_alter_stocking_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyparameter',
            name='water_level_morning_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='dailyparameter',
            name='water_level_evening_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='dailyparameter',
            name='transparency_morning',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='dailyparameter',
            name='transparency_evening',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='dailyparameter',
            name='water_color_morning',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='dailyparameter',
            name='water_color_evening',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
