from django.db import migrations, models
import django.db.models.deletion


def infer_category(description):
    text = (description or '').lower()
    mapping = [
        (('pakan', 'feed'), 'Pakan'),
        (('benur', 'bibit'), 'Benur'),
        (('probiotik', 'obat', 'mineral', 'vitamin'), 'Obat & Probiotik'),
        (('listrik', 'pln'), 'Listrik'),
        (('bbm', 'solar', 'bensin'), 'BBM'),
        (('gaji', 'upah', 'tenaga kerja'), 'Tenaga Kerja'),
        (('peralatan', 'alat', 'freezer', 'mesin'), 'Peralatan'),
        (('perbaikan', 'service', 'servis'), 'Perbaikan'),
        (('transport', 'ongkir'), 'Transportasi'),
        (('panen',), 'Panen'),
        (('pajak',), 'Pajak'),
        (('administrasi', 'admin'), 'Administrasi'),
    ]
    for keywords, category in mapping:
        if any(keyword in text for keyword in keywords):
            return category
    return 'Lain-lain'


def create_expenses_for_existing_payments(apps, schema_editor):
    TradePayment = apps.get_model('finance', 'TradePayment')
    OperationalExpense = apps.get_model('finance', 'OperationalExpense')
    for payment in TradePayment.objects.select_related('trade_account').filter(
        trade_account__account_type='payable'
    ).iterator():
        account = payment.trade_account
        description = account.description or 'Utang Usaha'
        OperationalExpense.objects.update_or_create(
            trade_payment_id=payment.pk,
            defaults={
                'cycle_id': account.cycle_id,
                'date': payment.payment_date,
                'category': infer_category(description),
                'pond_id': None,
                'name': f'Pelunasan Utang - {description}'[:150],
                'amount': payment.amount,
                'payment_method': payment.payment_method or 'Transfer',
                'notes': (
                    f'Beban basis kas dari pembayaran utang kepada {account.partner_name}. '
                    f'Dokumen utang: {account.document_number or "-"}. '
                    f'Bukti pembayaran: {payment.document_number or "-"}.'
                ),
                'is_fiscal_deductible': True,
                'document_number': payment.document_number or account.document_number or '',
                'is_capital_expenditure': False,
                'fixed_asset_id': None,
            },
        )


def remove_generated_expenses(apps, schema_editor):
    OperationalExpense = apps.get_model('finance', 'OperationalExpense')
    OperationalExpense.objects.filter(trade_payment__isnull=False).delete()


class Migration(migrations.Migration):
    dependencies = [('finance', '0014_operationalexpense_supplier_name_default')]
    operations = [
        migrations.AddField(
            model_name='operationalexpense',
            name='trade_payment',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='operational_expense',
                to='finance.tradepayment',
                verbose_name='Pembayaran utang sumber',
            ),
        ),
        migrations.RunPython(create_expenses_for_existing_payments, remove_generated_expenses),
    ]
