from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from sales.models import Sale
from .models import (
    BalanceEntry, FixedAsset, JournalEntry, JournalLine, LedgerAccount,
    OperationalExpense, OtherRevenue, TradeAccount, TradePayment
)


ACCOUNT_DEFINITIONS = [
    ('1101','Kas Tunai','asset','debit','Kas dan Bank'),
    ('1102','Bank BCA','asset','debit','Kas dan Bank'),
    ('1103','Bank Lainnya','asset','debit','Kas dan Bank'),
    ('1201','Piutang Usaha','asset','debit','Piutang Usaha'),
    ('1301','Persediaan','asset','debit','Persediaan'),
    ('1401','Uang Muka','asset','debit','Uang Muka'),
    ('1501','Aset Lancar Lainnya','asset','debit','Aset Lancar Lainnya'),
    ('1601','Aset Tetap','asset','debit','Aset Tetap'),
    ('1602','Akumulasi Penyusutan','asset','credit','Aset Tetap'),
    ('2101','Utang Usaha','liability','credit','Utang Usaha'),
    ('2201','Utang Pajak','liability','credit','Utang Pajak'),
    ('2301','Utang Pemilik','liability','credit','Utang Pemilik'),
    ('2401','Utang Lainnya','liability','credit','Utang Lainnya'),
    ('3101','Modal Pemilik','equity','credit','Modal'),
    ('3102','Tambahan Modal','equity','credit','Modal'),
    ('3103','Prive','equity','debit','Modal'),
    ('3201','Laba Ditahan','equity','credit','Laba Ditahan'),
    ('3299','Selisih Saldo Awal','equity','credit','Saldo Awal'),
    ('4101','Pendapatan Penjualan','revenue','credit','Pendapatan'),
    ('4201','Pendapatan Lain-lain','revenue','credit','Pendapatan'),
    ('5101','Beban Operasional','expense','debit','Beban'),
    ('5102','Beban Penyusutan','expense','debit','Beban'),
    ('5199','Beban Belum Diklasifikasikan','expense','debit','Beban'),
]


def ensure_accounts():
    result = {}
    for code, name, account_type, normal_balance, group in ACCOUNT_DEFINITIONS:
        account, _ = LedgerAccount.objects.update_or_create(
            code=code,
            defaults={
                'name': name, 'account_type': account_type,
                'normal_balance': normal_balance, 'group': group,
                'is_active': True, 'is_system': True,
            }
        )
        result[code] = account
    return result


def _money(value):
    return Decimal(value or 0).quantize(Decimal('0.01'))


def _post(source_type, source_id, date, reference, description, lines):
    clean_lines = [(account, _money(debit), _money(credit), note)
                   for account, debit, credit, note in lines
                   if _money(debit) or _money(credit)]
    debit_total = sum((line[1] for line in clean_lines), Decimal('0'))
    credit_total = sum((line[2] for line in clean_lines), Decimal('0'))
    if debit_total != credit_total:
        raise ValueError(f'Jurnal {source_type}:{source_id} tidak seimbang: {debit_total} != {credit_total}')

    entry, _ = JournalEntry.objects.update_or_create(
        source_type=source_type, source_id=source_id, is_system_generated=True,
        defaults={
            'date': date, 'reference': reference[:100],
            'description': description[:255], 'status': JournalEntry.STATUS_POSTED,
            'posted_at': timezone.now(),
        }
    )
    entry.lines.all().delete()
    JournalLine.objects.bulk_create([
        JournalLine(entry=entry, account=account, debit=debit, credit=credit, description=note[:255])
        for account, debit, credit, note in clean_lines
    ])
    return entry


def _cash_account(accounts, method):
    method = (method or '').lower()
    return accounts['1101'] if method in ('cash','tunai') else accounts['1102']


def _account_for_balance_entry(accounts, entry):
    name = (entry.account_name or '').lower()
    group = entry.group or ''
    if entry.account_type == BalanceEntry.ASSET:
        if 'bca' in name: return accounts['1102']
        if 'kas' in name or 'tunai' in name: return accounts['1101']
        if group == 'Piutang Usaha': return accounts['1201']
        if group == 'Persediaan': return accounts['1301']
        if group == 'Uang Muka': return accounts['1401']
        if group == 'Aset Tetap': return accounts['1601']
        return accounts['1501']
    if entry.account_type == BalanceEntry.LIABILITY:
        if group == 'Utang Usaha': return accounts['2101']
        if group == 'Utang Pajak': return accounts['2201']
        if group == 'Utang Pemilik': return accounts['2301']
        return accounts['2401']
    if group == 'Modal Pemilik': return accounts['3101']
    if group == 'Tambahan Modal': return accounts['3102']
    if group == 'Prive': return accounts['3103']
    return accounts['3201']


@transaction.atomic
def rebuild_system_ledger(as_of=None):
    as_of = as_of or timezone.localdate()
    accounts = ensure_accounts()
    JournalEntry.objects.filter(is_system_generated=True).delete()

    # Hanya posisi saldo awal terakhir untuk setiap akun.
    latest = {}
    for item in BalanceEntry.objects.filter(as_of_date__lte=as_of).order_by('account_name','-as_of_date','-id'):
        latest.setdefault((item.account_type,item.group,item.account_name), item)

    opening_lines = []
    for item in latest.values():
        amount = _money(item.amount)
        account = _account_for_balance_entry(accounts, item)
        if not amount:
            continue
        if account.normal_balance == LedgerAccount.NORMAL_DEBIT:
            opening_lines.append((account, amount, 0, item.account_name))
        else:
            opening_lines.append((account, 0, amount, item.account_name))

    opening_debit = sum((_money(x[1]) for x in opening_lines), Decimal('0'))
    opening_credit = sum((_money(x[2]) for x in opening_lines), Decimal('0'))
    opening_difference = opening_debit - opening_credit
    if opening_difference > 0:
        opening_lines.append((accounts['3299'], 0, opening_difference, 'Selisih sumber saldo awal'))
    elif opening_difference < 0:
        opening_lines.append((accounts['3299'], abs(opening_difference), 0, 'Selisih sumber saldo awal'))
    if opening_lines:
        first_date = min((item.as_of_date for item in latest.values()), default=as_of)
        _post('opening_balance', 1, first_date, 'OPENING', 'Saldo awal buku besar', opening_lines)

    invalid_status = ['Gagal','Expired','Dibatalkan','Refund']
    for sale in Sale.objects.filter(date__date__lte=as_of).exclude(status__in=invalid_status):
        amount = _money(sale.total_amount)
        paid = min(amount, _money(sale.cash_amount)+_money(sale.transfer_amount)+_money(sale.qris_amount)+_money(sale.other_payment_amount))
        if sale.status == 'Lunas' and paid == 0:
            paid = amount
        unpaid = max(amount-paid, Decimal('0'))
        debit_lines = []
        if paid:
            debit_lines.append((_cash_account(accounts, sale.payment_method), paid, 0, 'Penerimaan penjualan'))
        if unpaid:
            debit_lines.append((accounts['1201'], unpaid, 0, 'Piutang penjualan'))
        _post('sale', sale.pk, sale.date.date(), sale.invoice_no, 'Penjualan udang', debit_lines + [
            (accounts['4101'], 0, amount, 'Pendapatan penjualan')
        ])

    for revenue in OtherRevenue.objects.filter(date__lte=as_of):
        amount = _money(revenue.gross_amount)
        _post('other_revenue', revenue.pk, revenue.date, revenue.document_number or f'REV-{revenue.pk}', revenue.description, [
            (_cash_account(accounts, revenue.payment_method), amount, 0, 'Penerimaan'),
            (accounts['4201'], 0, amount, 'Pendapatan lain-lain'),
        ])

    for expense in OperationalExpense.objects.filter(date__lte=as_of):
        amount = _money(expense.amount)
        debit_account = accounts['1601'] if expense.is_capital_expenditure else accounts['5101']
        _post('expense', expense.pk, expense.date, expense.document_number or f'EXP-{expense.pk}', expense.name, [
            (debit_account, amount, 0, expense.category),
            (_cash_account(accounts, expense.payment_method), 0, amount, 'Pembayaran'),
        ])

    # Utang non-penjualan dan pembayarannya.
    for account in TradeAccount.objects.filter(account_type=TradeAccount.PAYABLE, transaction_date__lte=as_of):
        amount = _money(account.original_amount)
        _post('payable', account.pk, account.transaction_date, account.document_number or f'AP-{account.pk}', account.description, [
            (accounts['5199'], amount, 0, 'Beban/asal utang belum diklasifikasikan'),
            (accounts['2101'], 0, amount, 'Utang usaha'),
        ])
        for payment in account.payments.filter(payment_date__lte=as_of):
            _post('payable_payment', payment.pk, payment.payment_date, payment.document_number or f'APP-{payment.pk}', 'Pembayaran utang', [
                (accounts['2101'], payment.amount, 0, 'Pelunasan utang'),
                (_cash_account(accounts, payment.payment_method), 0, payment.amount, 'Kas/Bank'),
            ])

    return {
        'opening_difference': opening_difference,
        'entries': JournalEntry.objects.filter(status=JournalEntry.STATUS_POSTED).count(),
        'lines': JournalLine.objects.filter(entry__status=JournalEntry.STATUS_POSTED).count(),
    }


def account_balances(as_of):
    rows = []
    for account in LedgerAccount.objects.filter(is_active=True).order_by('code'):
        totals = account.journal_lines.filter(
            entry__status=JournalEntry.STATUS_POSTED,
            entry__date__lte=as_of,
        ).aggregate(debit=Sum('debit'), credit=Sum('credit'))
        debit = _money(totals['debit'])
        credit = _money(totals['credit'])
        raw = debit-credit
        balance = raw if account.normal_balance == LedgerAccount.NORMAL_DEBIT else -raw
        rows.append({'account':account,'debit':debit,'credit':credit,'balance':balance})
    return rows


def ledger_report(as_of):
    rows = account_balances(as_of)
    assets = [r for r in rows if r['account'].account_type == LedgerAccount.ASSET]
    liabilities = [r for r in rows if r['account'].account_type == LedgerAccount.LIABILITY]
    equities = [r for r in rows if r['account'].account_type == LedgerAccount.EQUITY]
    revenues = [r for r in rows if r['account'].account_type == LedgerAccount.REVENUE]
    expenses = [r for r in rows if r['account'].account_type == LedgerAccount.EXPENSE]

    total_assets = sum((r['balance'] for r in assets), Decimal('0'))
    total_liabilities = sum((r['balance'] for r in liabilities), Decimal('0'))
    opening_equity = sum((r['balance'] for r in equities), Decimal('0'))
    revenue = sum((r['balance'] for r in revenues), Decimal('0'))
    expense = sum((r['balance'] for r in expenses), Decimal('0'))
    current_profit = revenue-expense
    total_equity = opening_equity+current_profit
    difference = total_assets-total_liabilities-total_equity
    suspense = next((r['balance'] for r in equities if r['account'].code == '3299'), Decimal('0'))

    return {
        'rows':rows,'assets':assets,'liabilities':liabilities,'equities':equities,
        'revenues':revenues,'expenses':expenses,'total_assets':total_assets,
        'total_liabilities':total_liabilities,'opening_equity':opening_equity,
        'current_profit':current_profit,'total_equity':total_equity,
        'difference':difference,'opening_suspense':suspense,
    }
