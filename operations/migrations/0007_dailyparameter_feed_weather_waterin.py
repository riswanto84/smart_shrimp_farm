from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0006_dailyparameter_pagi_sore_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyparameter',
            name='feed_code',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='dailyparameter',
            name='water_in_cm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='dailyparameter',
            name='weather',
            field=models.CharField(blank=True, choices=[('Cerah', 'Cerah'), ('Berawan', 'Berawan'), ('Hujan', 'Hujan'), ('Panas', 'Panas'), ('Angin Kencang', 'Angin Kencang')], max_length=30),
        ),
    ]
