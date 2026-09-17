import base64
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


class MidtransError(Exception):
    """Error integrasi Midtrans yang aman ditampilkan ke admin aplikasi."""


def _is_production():
    return str(getattr(settings, 'MIDTRANS_IS_PRODUCTION', False)).lower() in {'1', 'true', 'yes', 'on'}


def _server_key():
    key = getattr(settings, 'MIDTRANS_SERVER_KEY', '') or ''
    if not key:
        raise MidtransError('MIDTRANS_SERVER_KEY belum diisi. Atur dahulu di file .env / environment server.')
    return key


def _snap_base_url():
    return 'https://app.midtrans.com/snap/v1' if _is_production() else 'https://app.sandbox.midtrans.com/snap/v1'


def _api_base_url():
    return 'https://api.midtrans.com/v2' if _is_production() else 'https://api.sandbox.midtrans.com/v2'


def _auth_headers():
    token = base64.b64encode((_server_key() + ':').encode('utf-8')).decode('ascii')
    return {
        'Authorization': f'Basic {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }


def _idr(value):
    amount = Decimal(value or 0).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return int(amount)


def _absolute_url(request, path):
    base = (getattr(settings, 'APP_BASE_URL', '') or '').rstrip('/')
    if base:
        return base + path
    return request.build_absolute_uri(path)


def _customer_details(sale):
    if not sale.customer:
        return {'first_name': 'Pelanggan Umum'}
    full_name = sale.customer.name or 'Pelanggan'
    parts = full_name.split(' ', 1)
    data = {'first_name': parts[0]}
    if len(parts) > 1:
        data['last_name'] = parts[1]
    if sale.customer.email:
        data['email'] = sale.customer.email
    if sale.customer.phone:
        data['phone'] = sale.customer.phone
    if sale.customer.address:
        data['billing_address'] = {'address': sale.customer.address}
    return data


def build_snap_payload(sale, request):
    """Payload Snap sederhana: satu item detail berisi total nota.

    Menggunakan satu item membuat gross_amount selalu cocok dengan total nota,
    termasuk ketika ada berat desimal, ongkos kirim, pengepakan, dan biaya lain.
    """
    gross_amount = _idr(sale.total_amount)
    if gross_amount <= 0:
        raise MidtransError('Total nota harus lebih dari Rp0 untuk membuat pembayaran Midtrans.')

    if not sale.midtrans_order_id:
        sale.midtrans_order_id = f'UEN-{sale.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        sale.save(update_fields=['midtrans_order_id'])

    invoice_path = reverse('sales:invoice', kwargs={'pk': sale.pk})
    return {
        'transaction_details': {
            'order_id': sale.midtrans_order_id,
            'gross_amount': gross_amount,
        },
        'item_details': [
            {
                'id': f'NOTA-{sale.id}',
                'price': gross_amount,
                'quantity': 1,
                'name': f'Nota Udang {sale.invoice_no}'[:50],
            }
        ],
        'customer_details': _customer_details(sale),
        'callbacks': {
            'finish': _absolute_url(request, invoice_path),
            'unfinish': _absolute_url(request, invoice_path),
            'error': _absolute_url(request, invoice_path),
        },
        'expiry': {
            'unit': 'hours',
            'duration': 24,
        },
    }


def create_snap_transaction(sale, request):
    payload = build_snap_payload(sale, request)
    try:
        response = requests.post(
            f'{_snap_base_url()}/transactions',
            data=json.dumps(payload),
            headers=_auth_headers(),
            timeout=25,
        )
    except requests.RequestException as exc:
        raise MidtransError(f'Gagal menghubungi Midtrans: {exc}') from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise MidtransError(f'Respons Midtrans tidak valid. HTTP {response.status_code}') from exc

    if response.status_code not in (200, 201):
        message = data.get('error_messages') or data.get('message') or data
        raise MidtransError(f'Midtrans menolak transaksi: {message}')

    sale.midtrans_snap_token = data.get('token', '')
    sale.midtrans_payment_url = data.get('redirect_url', '')
    sale.payment_method = 'Midtrans'
    sale.status = 'Menunggu Pembayaran'
    sale.midtrans_status = 'snap_created'
    sale.midtrans_raw_response = data
    sale.save(update_fields=[
        'midtrans_snap_token', 'midtrans_payment_url', 'payment_method',
        'status', 'midtrans_status', 'midtrans_raw_response'
    ])
    from finance.receivable_sync import sync_sale_receivable
    sync_sale_receivable(sale)
    return data


def verify_notification_signature(payload):
    order_id = str(payload.get('order_id', ''))
    status_code = str(payload.get('status_code', ''))
    gross_amount = str(payload.get('gross_amount', ''))
    signature_key = str(payload.get('signature_key', ''))
    raw = order_id + status_code + gross_amount + _server_key()
    expected = hashlib.sha512(raw.encode('utf-8')).hexdigest()
    return signature_key and expected == signature_key


def map_midtrans_status(transaction_status, fraud_status=''):
    transaction_status = transaction_status or ''
    fraud_status = fraud_status or ''
    if transaction_status == 'capture':
        return 'Lunas' if fraud_status == 'accept' else 'Menunggu Pembayaran'
    if transaction_status == 'settlement':
        return 'Lunas'
    if transaction_status == 'pending':
        return 'Menunggu Pembayaran'
    if transaction_status == 'expire':
        return 'Expired'
    if transaction_status == 'cancel':
        return 'Dibatalkan'
    if transaction_status in {'deny', 'failure'}:
        return 'Gagal'
    if transaction_status in {'refund', 'partial_refund'}:
        return 'Refund'
    return 'Menunggu Pembayaran'


def apply_midtrans_status(sale, payload):
    transaction_status = payload.get('transaction_status', '')
    fraud_status = payload.get('fraud_status', '')
    sale.status = map_midtrans_status(transaction_status, fraud_status)
    sale.payment_method = 'Midtrans'
    sale.midtrans_status = transaction_status or sale.midtrans_status
    sale.midtrans_transaction_id = payload.get('transaction_id', sale.midtrans_transaction_id) or ''
    sale.midtrans_payment_type = payload.get('payment_type', sale.midtrans_payment_type) or ''
    sale.midtrans_raw_response = payload
    if sale.status == 'Lunas' and not sale.paid_at:
        sale.paid_at = timezone.now()
    sale.save(update_fields=[
        'status', 'payment_method', 'midtrans_status', 'midtrans_transaction_id',
        'midtrans_payment_type', 'midtrans_raw_response', 'paid_at'
    ])
    from finance.receivable_sync import sync_sale_receivable
    sync_sale_receivable(sale)
    return sale


def get_transaction_status(sale):
    if not sale.midtrans_order_id:
        raise MidtransError('Nota ini belum memiliki Midtrans Order ID.')
    try:
        response = requests.get(
            f'{_api_base_url()}/{sale.midtrans_order_id}/status',
            headers=_auth_headers(),
            timeout=25,
        )
    except requests.RequestException as exc:
        raise MidtransError(f'Gagal mengecek status Midtrans: {exc}') from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise MidtransError(f'Respons status Midtrans tidak valid. HTTP {response.status_code}') from exc

    if response.status_code not in (200, 201):
        message = data.get('status_message') or data.get('error_messages') or data
        raise MidtransError(f'Gagal cek status Midtrans: {message}')
    return data
