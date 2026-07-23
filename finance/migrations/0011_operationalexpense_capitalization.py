from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('finance', '0010_tradeaccount_customer')]

    operations = [
        migrations.AddField(
            model_name='operationalexpense',
            name='is_capital_expenditure',
            field=models.BooleanField(default=False, verbose_name='Pembelian aset/kapitalisasi'),
        ),
        migrations.AddField(
            model_name='operationalexpense',
            name='fixed_asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_expenses', to='finance.fixedasset', verbose_name='Aset terkait'),
        ),
    ]
