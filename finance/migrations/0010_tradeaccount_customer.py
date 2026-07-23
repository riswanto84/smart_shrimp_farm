from django.db import migrations, models
import django.db.models.deletion


def backfill_customer(apps, schema_editor):
    TradeAccount = apps.get_model('finance', 'TradeAccount')
    Customer = apps.get_model('sales', 'Customer')
    for account in TradeAccount.objects.filter(account_type='receivable', customer__isnull=True).iterator():
        name = (account.partner_name or '').strip()
        if not name or name == 'Pelanggan Umum':
            continue
        customer = Customer.objects.filter(name__iexact=name).first()
        if customer:
            account.customer_id = customer.pk
            account.save(update_fields=['customer'])


class Migration(migrations.Migration):
    dependencies = [
        ('sales', '0007_sale_mixed_payment_documents'),
        ('finance', '0009_expensedocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradeaccount',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='receivables', to='sales.customer', verbose_name='Pelanggan'),
        ),
        migrations.RunPython(backfill_customer, migrations.RunPython.noop),
    ]
