from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('cultivation', '0002_cycle_snapshot_and_completed_at')]

    operations = [
        migrations.AddField(model_name='cultivationcycle', name='target_doc', field=models.PositiveIntegerField(default=120, help_text='Target DOC panen.')),
        migrations.AddField(model_name='cultivationcycle', name='target_size', field=models.DecimalField(decimal_places=2, default=Decimal('30'), help_text='Target size panen (ekor/kg).', max_digits=6)),
        migrations.AddField(model_name='cultivationcycle', name='target_biomass_ton', field=models.DecimalField(decimal_places=2, default=Decimal('25'), help_text='Target biomassa/produksi dalam ton.', max_digits=10)),
        migrations.AddField(model_name='cultivationcycle', name='target_sr_percent', field=models.DecimalField(decimal_places=2, default=Decimal('85'), help_text='Target survival rate dalam persen.', max_digits=6)),
        migrations.AddField(model_name='cultivationcycle', name='target_fcr', field=models.DecimalField(decimal_places=2, default=Decimal('1.20'), help_text='Target feed conversion ratio.', max_digits=6)),
        migrations.AddField(model_name='cultivationcycle', name='target_adg', field=models.DecimalField(decimal_places=3, default=Decimal('0.25'), help_text='Target ADG gram per hari.', max_digits=7)),
        migrations.AddField(model_name='cultivationcycle', name='target_population', field=models.PositiveBigIntegerField(blank=True, default=0, help_text='Target populasi hidup saat panen; 0 berarti tidak ditetapkan.')),
        migrations.AddField(model_name='cultivationcycle', name='estimated_price_per_kg', field=models.DecimalField(blank=True, decimal_places=2, default=0, help_text='Harga jual estimasi per kilogram.', max_digits=14)),
        migrations.AddField(model_name='cultivationcycle', name='target_cost', field=models.DecimalField(blank=True, decimal_places=2, default=0, help_text='Target biaya produksi satu siklus.', max_digits=18)),
    ]
