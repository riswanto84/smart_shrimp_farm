from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0001_initial'),
        ('ponds', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyPondRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('doc', models.PositiveIntegerField(default=0)),
                ('feed_code', models.CharField(blank=True, max_length=80)),
                ('daily_feed_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('water_in_cm', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('weather', models.CharField(blank=True, choices=[('Cerah', 'Cerah'), ('Berawan', 'Berawan'), ('Hujan', 'Hujan'), ('Panas', 'Panas'), ('Angin Kencang', 'Angin Kencang')], max_length=30)),
                ('treatment', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pond', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_records', to='ponds.pond')),
                ('technician', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', 'pond__name'], 'unique_together': {('pond', 'date')}},
        ),
        migrations.CreateModel(
            name='AncoCheck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('doc', models.PositiveIntegerField(default=0)),
                ('anco1_morning', models.CharField(choices=[('H', 'Habis'), ('S', 'Sisa'), ('SS', 'Sisa Banyak'), ('-', 'Tidak Dicek')], default='-', max_length=2)),
                ('anco2_morning', models.CharField(choices=[('H', 'Habis'), ('S', 'Sisa'), ('SS', 'Sisa Banyak'), ('-', 'Tidak Dicek')], default='-', max_length=2)),
                ('anco1_noon', models.CharField(choices=[('H', 'Habis'), ('S', 'Sisa'), ('SS', 'Sisa Banyak'), ('-', 'Tidak Dicek')], default='-', max_length=2)),
                ('anco2_noon', models.CharField(choices=[('H', 'Habis'), ('S', 'Sisa'), ('SS', 'Sisa Banyak'), ('-', 'Tidak Dicek')], default='-', max_length=2)),
                ('anco1_evening', models.CharField(choices=[('H', 'Habis'), ('S', 'Sisa'), ('SS', 'Sisa Banyak'), ('-', 'Tidak Dicek')], default='-', max_length=2)),
                ('anco2_evening', models.CharField(choices=[('H', 'Habis'), ('S', 'Sisa'), ('SS', 'Sisa Banyak'), ('-', 'Tidak Dicek')], default='-', max_length=2)),
                ('appetite_status', models.CharField(blank=True, max_length=80)),
                ('recommendation', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pond', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='anco_checks', to='ponds.pond')),
                ('technician', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', 'pond__name'], 'unique_together': {('pond', 'date')}},
        ),
        migrations.CreateModel(
            name='SamplingRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('doc', models.PositiveIntegerField(default=0)),
                ('sample_weight_g', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('sample_count', models.PositiveIntegerField(default=0)),
                ('abw_g', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('size', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('adg_weekly', models.DecimalField(decimal_places=3, default=0, max_digits=8)),
                ('adg_cumulative', models.DecimalField(decimal_places=3, default=0, max_digits=8)),
                ('estimated_sr', models.DecimalField(decimal_places=2, default=90, max_digits=6)),
                ('biomass_kg', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('fcr', models.DecimalField(decimal_places=3, default=0, max_digits=8)),
                ('population', models.PositiveIntegerField(default=0)),
                ('cumulative_feed_kg', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('stocking_count', models.PositiveIntegerField(default=0)),
                ('fr_percent', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('index_score', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('harvest_estimation', models.CharField(blank=True, max_length=160)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pond', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sampling_records', to='ponds.pond')),
            ],
            options={'ordering': ['-date', 'pond__name']},
        ),
        migrations.CreateModel(
            name='SiphonRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('doc', models.PositiveIntegerField(default=0)),
                ('dead_count', models.PositiveIntegerField(default=0)),
                ('live_count', models.PositiveIntegerField(default=0)),
                ('daily_total', models.PositiveIntegerField(default=0)),
                ('accumulated_total', models.PositiveIntegerField(default=0)),
                ('health_indicator', models.CharField(blank=True, max_length=120)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pond', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='siphon_records', to='ponds.pond')),
                ('technician', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', 'pond__name'], 'unique_together': {('pond', 'date')}},
        ),
    ]
