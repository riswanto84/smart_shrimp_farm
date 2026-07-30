from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('cultivation', '0003_cycle_production_targets'),
        ('finance', '0005_tax_reports_assets_and_balance'),
    ]

    operations = [
        migrations.CreateModel(
            name='TradeAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_type', models.CharField(choices=[('receivable', 'Piutang Usaha'), ('payable', 'Utang Usaha')], max_length=20)),
                ('transaction_date', models.DateField(verbose_name='Tanggal transaksi')),
                ('due_date', models.DateField(verbose_name='Tanggal jatuh tempo')),
                ('document_number', models.CharField(blank=True, max_length=80, verbose_name='Nomor dokumen')),
                ('partner_name', models.CharField(max_length=180, verbose_name='Pelanggan/Supplier')),
                ('description', models.CharField(max_length=220)),
                ('original_amount', models.DecimalField(decimal_places=2, max_digits=16, verbose_name='Nilai awal')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cycle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='trade_accounts', to='cultivation.cultivationcycle')),
            ],
            options={'ordering': ['due_date', 'transaction_date', 'id']},
        ),
        migrations.CreateModel(
            name='TradePayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_date', models.DateField(verbose_name='Tanggal pembayaran')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=16)),
                ('payment_method', models.CharField(choices=[('Transfer', 'Transfer'), ('Cash', 'Tunai'), ('Giro', 'Giro'), ('Lainnya', 'Lainnya')], default='Transfer', max_length=30)),
                ('document_number', models.CharField(blank=True, max_length=80, verbose_name='Nomor bukti')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('trade_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='finance.tradeaccount')),
            ],
            options={'ordering': ['payment_date', 'id']},
        ),
        migrations.AddIndex(model_name='tradeaccount', index=models.Index(fields=['account_type', 'due_date'], name='finance_tra_account_8d922a_idx')),
        migrations.AddIndex(model_name='tradeaccount', index=models.Index(fields=['partner_name'], name='finance_tra_partner_297cc4_idx')),
    ]
