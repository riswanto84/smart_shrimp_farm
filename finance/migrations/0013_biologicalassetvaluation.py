from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('finance', '0012_operationalexpense_payment_status_default'),
    ]

    operations = [
        migrations.CreateModel(
            name='BiologicalAssetValuation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valuation_date', models.DateField(unique=True, verbose_name='Tanggal penilaian')),
                ('closing_value', models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Nilai aset biologis')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='biological_valuations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Penilaian Aset Biologis',
                'verbose_name_plural': 'Penilaian Aset Biologis',
                'ordering': ['valuation_date', 'id'],
            },
        ),
    ]
