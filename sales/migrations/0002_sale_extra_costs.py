from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='shipping_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Ongkos kirim'),
        ),
        migrations.AddField(
            model_name='sale',
            name='packing_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Biaya pengepakan'),
        ),
        migrations.AddField(
            model_name='sale',
            name='other_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Biaya lainnya'),
        ),
    ]
