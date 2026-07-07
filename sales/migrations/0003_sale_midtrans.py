from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0002_sale_extra_costs'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='midtrans_order_id',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name='sale',
            name='midtrans_transaction_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='sale',
            name='midtrans_snap_token',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='sale',
            name='midtrans_payment_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='sale',
            name='midtrans_payment_type',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='sale',
            name='midtrans_status',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='sale',
            name='midtrans_raw_response',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='sale',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sale',
            name='expired_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
