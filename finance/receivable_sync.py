"""Sinkronisasi otomatis Nota Penjualan dengan kartu Piutang Usaha.

Modul ini sengaja tidak menambah relasi database baru agar pembaruan dapat
langsung dipasang tanpa migrasi. Kartu otomatis dikenali melalui penanda unik
pada kolom ``notes``.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import TradeAccount, TradePayment

OPEN_SALE_STATUSES = {'Belum Lunas', 'Menunggu Pembayaran'}
CLOSED_SALE_STATUSES = {'Gagal', 'Expired', 'Dibatalkan', 'Refund'}
AUTO_NOTE_PREFIX = 'AUTO_FROM_SALE:'
AUTO_PAYMENT_PREFIX = 'AUTO-SALE-'
DEFAULT_DUE_DAYS = 30


def _money(value):
    try:
        return Decimal(value or 0)
    except Exception:
        return Decimal('0')


def sale_paid_amount(sale):
    """Jumlah pembayaran riil yang telah dicatat pada nota.

    Untuk nota yang sudah ditandai Lunas, jumlah dibayar disamakan dengan total
    nota agar kartu piutang tertutup walaupun nota lama belum mempunyai rincian
    metode pembayaran.
    """
    total = max(_money(sale.total_amount), Decimal('0'))
    paid = sum((
        _money(getattr(sale, 'cash_amount', 0)),
        _money(getattr(sale, 'transfer_amount', 0)),
        _money(getattr(sale, 'qris_amount', 0)),
        _money(getattr(sale, 'other_payment_amount', 0)),
    ), Decimal('0'))
    # Nota lama kadang berstatus Lunas tanpa rincian nominal pembayaran.
    # Hanya pada kondisi itu pembayaran dianggap sama dengan total nota.
    if sale.status == 'Lunas' and paid <= 0:
        return total
    return min(max(paid, Decimal('0')), total)


def _sale_date(sale):
    value = sale.date
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.date()


def _payment_method(sale):
    method = sale.payment_method
    if method == 'Cash':
        return 'Cash'
    if method in {'Transfer', 'QRIS', 'Midtrans'}:
        return 'Transfer'
    return 'Lainnya'


def _marker(sale):
    return f'{AUTO_NOTE_PREFIX}{sale.pk}'


def _get_synced_account(sale):
    return TradeAccount.objects.filter(
        account_type=TradeAccount.RECEIVABLE,
        notes__contains=_marker(sale),
    ).first()


@transaction.atomic
def sync_sale_receivable(sale):
    """Membuat/memperbarui kartu piutang untuk satu nota.

    - Belum Lunas / Menunggu Pembayaran: kartu dibuat atau diperbarui.
    - Lunas: kartu yang sudah ada ditutup, tetapi kartu baru tidak dibuat.
    - Gagal / Expired / Dibatalkan / Refund: kartu otomatis dihapus.
    """
    account = _get_synced_account(sale)

    if sale.status in CLOSED_SALE_STATUSES:
        if account:
            account.delete()
        return None

    if sale.status not in OPEN_SALE_STATUSES and sale.status != 'Lunas':
        return account

    # Nota lunas yang sejak awal tidak pernah menjadi piutang tidak perlu masuk
    # daftar kartu piutang.
    if sale.status == 'Lunas' and account is None:
        return None

    transaction_date = _sale_date(sale)
    total = max(_money(sale.total_amount), Decimal('0'))
    customer_name = sale.customer.name if sale.customer else 'Pelanggan Umum'
    marker = _marker(sale)
    notes = marker
    if sale.notes:
        notes += f'\nCatatan nota: {sale.notes}'

    if account is None:
        account = TradeAccount.objects.create(
            cycle=sale.cycle,
            account_type=TradeAccount.RECEIVABLE,
            transaction_date=transaction_date,
            due_date=transaction_date + timedelta(days=DEFAULT_DUE_DAYS),
            document_number=sale.invoice_no,
            customer=sale.customer,
            partner_name=customer_name,
            description=f'Piutang otomatis dari Nota Penjualan {sale.invoice_no}',
            original_amount=total,
            notes=notes,
        )
    else:
        account.cycle = sale.cycle
        account.transaction_date = transaction_date
        # Pertahankan jatuh tempo yang mungkin sudah disesuaikan pengguna.
        if not account.due_date:
            account.due_date = transaction_date + timedelta(days=DEFAULT_DUE_DAYS)
        account.document_number = sale.invoice_no
        account.customer = sale.customer
        account.partner_name = customer_name
        account.description = f'Piutang otomatis dari Nota Penjualan {sale.invoice_no}'
        account.original_amount = total
        account.notes = notes
        account.save()

    auto_document_number = f'{AUTO_PAYMENT_PREFIX}{sale.pk}'
    paid = sale_paid_amount(sale)
    auto_payment = TradePayment.objects.filter(
        trade_account=account,
        document_number=auto_document_number,
    ).first()

    if paid > 0:
        defaults = {
            'payment_date': sale.paid_at.date() if sale.paid_at else transaction_date,
            'amount': paid,
            'payment_method': _payment_method(sale),
            'notes': 'Pembayaran otomatis berdasarkan rincian pembayaran pada nota penjualan.',
        }
        if auto_payment:
            for field, value in defaults.items():
                setattr(auto_payment, field, value)
            auto_payment.save()
        else:
            TradePayment.objects.create(
                trade_account=account,
                document_number=auto_document_number,
                **defaults,
            )
    elif auto_payment:
        auto_payment.delete()

    return account


def sync_open_sales():
    """Backfill nota lama yang masih terbuka dan segarkan kartu otomatis."""
    from sales.models import Sale

    count = 0
    sales = Sale.objects.filter(status__in=OPEN_SALE_STATUSES).select_related('customer', 'cycle')
    for sale in sales.iterator():
        if sync_sale_receivable(sale):
            count += 1
    return count


def sync_all_sales():
    """Sinkronisasi menyeluruh untuk command pemeliharaan."""
    from sales.models import Sale

    count = 0
    for sale in Sale.objects.select_related('customer', 'cycle').iterator():
        if sync_sale_receivable(sale):
            count += 1
    return count
