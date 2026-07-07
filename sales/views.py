from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from django.http import FileResponse, JsonResponse, HttpResponseBadRequest, HttpResponse
from django.db.models import Sum, Count
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Customer, Sale, SaleItem
from operations.models import Harvest
from .pdf import build_invoice_pdf, safe_invoice_filename
from .midtrans import (
    MidtransError, create_snap_transaction, verify_notification_signature,
    apply_midtrans_status, get_transaction_status,
)
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta
from decimal import Decimal
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf, rupiah
from core.utils import parse_rupiah
from core.pagination import paginate_queryset


def _get_sale_amounts_from_request(request):
    weight = parse_rupiah(request.POST.get('weight_kg'))
    price = parse_rupiah(request.POST.get('price_per_kg'))
    subtotal = weight * price
    shipping_cost = parse_rupiah(request.POST.get('shipping_cost'))
    packing_cost = parse_rupiah(request.POST.get('packing_cost'))
    other_cost = parse_rupiah(request.POST.get('other_cost'))
    total_amount = subtotal + shipping_cost + packing_cost + other_cost
    return weight, price, subtotal, shipping_cost, packing_cost, other_cost, total_amount


def _money(value):
    try:
        return Decimal(value or 0)
    except Exception:
        return Decimal('0')


def _default_month_range(request):
    """Filter dashboard penjualan. Default: bulan berjalan."""
    today = timezone.localdate()
    date_from = parse_date(request.GET.get('date_from') or '') or today.replace(day=1)
    date_to = parse_date(request.GET.get('date_to') or '') or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _filtered_sales_for_dashboard(request):
    date_from, date_to = _default_month_range(request)
    qs = Sale.objects.select_related('customer', 'cashier').prefetch_related('items').order_by('-date')
    qs = filter_by_date_range(qs, 'date', date_from, date_to, is_datetime=True)
    status = request.GET.get('status') or ''
    payment_method = request.GET.get('payment_method') or ''
    if status:
        qs = qs.filter(status=status)
    if payment_method:
        qs = qs.filter(payment_method=payment_method)
    return qs, date_from, date_to, status, payment_method


@login_required
@permission_required('sales.dashboard')
def sales_dashboard(request):
    sales, date_from, date_to, status_filter, payment_filter = _filtered_sales_for_dashboard(request)
    all_in_period = list(sales)

    total_revenue = sum((_money(s.total_amount) for s in all_in_period), Decimal('0'))
    total_kg = sum((_money(s.total_kg) for s in all_in_period), Decimal('0'))
    total_transactions = len(all_in_period)
    avg_price = (total_revenue / total_kg) if total_kg else Decimal('0')
    paid_revenue = sum((_money(s.total_amount) for s in all_in_period if s.status == 'Lunas'), Decimal('0'))
    receivable_revenue = sum((_money(s.total_amount) for s in all_in_period if s.status in ['Belum Lunas', 'Menunggu Pembayaran']), Decimal('0'))
    paid_count = sum(1 for s in all_in_period if s.status == 'Lunas')
    receivable_count = sum(1 for s in all_in_period if s.status in ['Belum Lunas', 'Menunggu Pembayaran'])

    # Grafik tren harian dibuat di Python agar aman untuk SQLite.
    daily = {}
    d = date_from
    while d <= date_to:
        daily[d.isoformat()] = {'label': d.strftime('%d/%m'), 'revenue': Decimal('0'), 'kg': Decimal('0'), 'count': 0}
        d += timedelta(days=1)
    for s in all_in_period:
        key = timezone.localtime(s.date).date().isoformat()
        if key not in daily:
            daily[key] = {'label': timezone.localtime(s.date).strftime('%d/%m'), 'revenue': Decimal('0'), 'kg': Decimal('0'), 'count': 0}
        daily[key]['revenue'] += _money(s.total_amount)
        daily[key]['kg'] += _money(s.total_kg)
        daily[key]['count'] += 1
    trend_rows = list(daily.values())
    max_revenue = max([row['revenue'] for row in trend_rows] or [Decimal('0')]) or Decimal('1')
    for row in trend_rows:
        row['revenue_width'] = int((row['revenue'] / max_revenue) * 100) if max_revenue else 0

    payment_map = {}
    status_map = {}
    customer_map = {}
    size_map = {}
    for s in all_in_period:
        payment_map.setdefault(s.payment_method or 'Lainnya', {'label': s.payment_method or 'Lainnya', 'amount': Decimal('0'), 'count': 0})
        payment_map[s.payment_method or 'Lainnya']['amount'] += _money(s.total_amount)
        payment_map[s.payment_method or 'Lainnya']['count'] += 1

        status_map.setdefault(s.status or 'Lainnya', {'label': s.status or 'Lainnya', 'amount': Decimal('0'), 'count': 0})
        status_map[s.status or 'Lainnya']['amount'] += _money(s.total_amount)
        status_map[s.status or 'Lainnya']['count'] += 1

        cname = s.customer.name if s.customer else 'Tanpa pelanggan'
        customer_map.setdefault(cname, {'label': cname, 'amount': Decimal('0'), 'kg': Decimal('0'), 'count': 0})
        customer_map[cname]['amount'] += _money(s.total_amount)
        customer_map[cname]['kg'] += _money(s.total_kg)
        customer_map[cname]['count'] += 1

        for item in s.items.all():
            size = item.size_text or 'Tidak diisi'
            size_map.setdefault(size, {'label': size, 'amount': Decimal('0'), 'kg': Decimal('0'), 'count': 0})
            size_map[size]['amount'] += _money(item.subtotal)
            size_map[size]['kg'] += _money(item.weight_kg)
            size_map[size]['count'] += 1

    payment_rows = sorted(payment_map.values(), key=lambda x: x['amount'], reverse=True)
    status_rows = sorted(status_map.values(), key=lambda x: x['amount'], reverse=True)
    top_customers = sorted(customer_map.values(), key=lambda x: x['amount'], reverse=True)[:8]
    size_rows = sorted(size_map.values(), key=lambda x: x['kg'], reverse=True)[:8]

    def add_width(rows, key='amount'):
        max_value = max([_money(r.get(key)) for r in rows] or [Decimal('0')]) or Decimal('1')
        for r in rows:
            r['width'] = int((_money(r.get(key)) / max_value) * 100) if max_value else 0
        return rows

    add_width(payment_rows, 'amount')
    add_width(status_rows, 'amount')
    add_width(top_customers, 'amount')
    add_width(size_rows, 'kg')

    recent_sales = all_in_period[:10]
    unpaid_sales = [s for s in all_in_period if s.status in ['Belum Lunas', 'Menunggu Pembayaran']][:10]

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'total_revenue': total_revenue,
        'paid_revenue': paid_revenue,
        'receivable_revenue': receivable_revenue,
        'total_kg': total_kg,
        'total_transactions': total_transactions,
        'avg_price': avg_price,
        'paid_count': paid_count,
        'receivable_count': receivable_count,
        'trend_rows': trend_rows[-31:],
        'payment_rows': payment_rows,
        'status_rows': status_rows,
        'top_customers': top_customers,
        'size_rows': size_rows,
        'recent_sales': recent_sales,
        'unpaid_sales': unpaid_sales,
        'payment_choices': Sale.PAYMENT,
        'status_choices': Sale.STATUS,
    }
    return render(request, 'sales/dashboard.html', context)


@login_required
@permission_required('sales.customers')
def customers(request):
    customers = Customer.objects.all().order_by('name')
    page_obj = paginate_queryset(request, customers, per_page=10)
    return render(request, 'sales/customers.html', {'customers': page_obj, 'page_obj': page_obj})


@login_required
@permission_required('sales.customers')
def add_customer(request):
    if request.method == 'POST':
        Customer.objects.create(name=request.POST['name'], phone=request.POST.get('phone', ''), email=request.POST.get('email', ''), address=request.POST.get('address', ''))
        return redirect('sales:customers')
    return render(request, 'sales/customer_form.html')


@login_required
@permission_required('sales.cashier')
def cashier(request):
    customers = Customer.objects.all(); harvests = Harvest.objects.order_by('-date')[:20]
    if request.method == 'POST':
        inv = 'INV' + timezone.now().strftime('%Y%m%d%H%M%S')
        weight, price, subtotal, shipping_cost, packing_cost, other_cost, total_amount = _get_sale_amounts_from_request(request)
        sale = Sale.objects.create(
            invoice_no=inv,
            customer_id=request.POST.get('customer') or None,
            total_kg=weight,
            total_amount=total_amount,
            shipping_cost=shipping_cost,
            packing_cost=packing_cost,
            other_cost=other_cost,
            payment_method=request.POST.get('payment_method', 'Cash'),
            status=request.POST.get('status', 'Lunas'),
            cashier=request.user,
            notes=request.POST.get('notes', ''),
        )
        SaleItem.objects.create(sale=sale, harvest_id=request.POST.get('harvest') or None, size_text=request.POST.get('size_text', ''), weight_kg=weight, price_per_kg=price, subtotal=subtotal)
        return redirect('sales:invoice', pk=sale.pk)
    return render(request, 'sales/cashier.html', {'customers': customers, 'harvests': harvests})



@login_required
@permission_required('sales.cashier')
def edit_sale(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer', 'cashier').prefetch_related('items'), pk=pk)
    customers = Customer.objects.all()
    harvests = Harvest.objects.order_by('-date')[:30]
    item = sale.items.first()

    if request.method == 'POST':
        invoice_no = (request.POST.get('invoice_no') or sale.invoice_no).strip()
        if Sale.objects.filter(invoice_no=invoice_no).exclude(pk=sale.pk).exists():
            messages.error(request, 'Nomor nota sudah digunakan. Silakan gunakan nomor nota lain.')
            return render(request, 'sales/sale_form.html', {'sale': sale, 'item': item, 'customers': customers, 'harvests': harvests, 'mode': 'edit'})

        weight, price, subtotal, shipping_cost, packing_cost, other_cost, total_amount = _get_sale_amounts_from_request(request)
        old_total_amount = sale.total_amount

        sale.invoice_no = invoice_no
        sale.customer_id = request.POST.get('customer') or None
        sale.total_kg = weight
        sale.total_amount = total_amount
        sale.shipping_cost = shipping_cost
        sale.packing_cost = packing_cost
        sale.other_cost = other_cost
        sale.payment_method = request.POST.get('payment_method', 'Cash')
        sale.status = request.POST.get('status', 'Lunas')
        sale.notes = request.POST.get('notes', '')
        if old_total_amount != total_amount and sale.status != 'Lunas':
            # Jika total nota berubah, link Snap lama tidak lagi sesuai nominal baru.
            sale.midtrans_order_id = ''
            sale.midtrans_snap_token = ''
            sale.midtrans_payment_url = ''
            sale.midtrans_status = ''
            sale.midtrans_transaction_id = ''
        sale.save()

        if item is None:
            item = SaleItem(sale=sale)
        item.harvest_id = request.POST.get('harvest') or None
        item.size_text = request.POST.get('size_text', '')
        item.weight_kg = weight
        item.price_per_kg = price
        item.subtotal = subtotal
        item.save()

        messages.success(request, 'Nota penjualan berhasil diperbarui.')
        return redirect('sales:invoice', pk=sale.pk)

    return render(request, 'sales/sale_form.html', {'sale': sale, 'item': item, 'customers': customers, 'harvests': harvests, 'mode': 'edit'})

def _sales_queryset(request):
    date_from, date_to = get_date_range(request)
    sales = Sale.objects.select_related('customer', 'cashier').order_by('-date')
    sales = filter_by_date_range(sales, 'date', date_from, date_to, is_datetime=True)
    status = request.GET.get('status') or ''
    if status:
        sales = sales.filter(status=status)
    return sales, date_from, date_to


def _sales_rows(sales):
    rows = []
    for s in sales:
        rows.append([
            s.date.strftime('%d/%m/%Y %H:%M'),
            s.invoice_no,
            s.customer.name if s.customer else '-',
            float(s.total_kg),
            rupiah(s.total_amount),
            s.payment_method,
            s.status,
            s.cashier.username if s.cashier else '-',
        ])
    return rows


@login_required
@permission_required('sales.invoices')
def invoices(request):
    sales, date_from, date_to = _sales_queryset(request)
    total = sales.aggregate(s=Sum('total_amount'))['s'] or 0
    total_kg = sales.aggregate(s=Sum('total_kg'))['s'] or 0
    page_obj = paginate_queryset(request, sales, per_page=10)
    return render(request, 'sales/invoices.html', {'sales': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'total': total, 'total_kg': total_kg})


@login_required
@permission_required('sales.invoices')
def export_sales_excel(request):
    sales, date_from, date_to = _sales_queryset(request)
    rows = _sales_rows(sales)
    total = sales.aggregate(s=Sum('total_amount'))['s'] or 0
    total_kg = sales.aggregate(s=Sum('total_kg'))['s'] or 0
    return export_excel(
        'laporan_penjualan',
        'Laporan Penjualan',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'No Nota', 'Pelanggan', 'Total Kg', 'Total Penjualan', 'Metode', 'Status', 'Kasir'],
        rows,
        [['', '', 'TOTAL', float(total_kg), rupiah(total), '', '', '']]
    )


@login_required
@permission_required('sales.invoices')
def export_sales_pdf(request):
    sales, date_from, date_to = _sales_queryset(request)
    rows = _sales_rows(sales)
    pdf_rows = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]] for r in rows]
    total = sales.aggregate(s=Sum('total_amount'))['s'] or 0
    total_kg = sales.aggregate(s=Sum('total_kg'))['s'] or 0
    return export_pdf(
        'laporan_penjualan',
        'Laporan Penjualan',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'No Nota', 'Pelanggan', 'Kg', 'Total', 'Metode', 'Status', 'Kasir'],
        pdf_rows,
        [['', '', 'TOTAL', total_kg, rupiah(total), '', '', '']]
    )


@login_required
@permission_required('sales.invoices')
def invoice(request, pk):
    return render(request, 'sales/invoice.html', {'sale': get_object_or_404(Sale, pk=pk)})


@login_required
@permission_required('sales.invoices')
def invoice_pdf(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    path = build_invoice_pdf(sale)
    return FileResponse(open(path, 'rb'), as_attachment=True, filename=f'{safe_invoice_filename(sale.invoice_no)}.pdf')


@login_required
@permission_required('sales.invoices')
@require_POST
def create_midtrans_payment(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer').prefetch_related('items'), pk=pk)
    if sale.status == 'Lunas':
        messages.info(request, 'Nota ini sudah berstatus Lunas. Pembayaran Midtrans tidak dibuat ulang.')
        return redirect('sales:invoice', pk=sale.pk)

    if sale.midtrans_payment_url and sale.status == 'Menunggu Pembayaran':
        return redirect(sale.midtrans_payment_url)

    if sale.status in {'Expired', 'Gagal', 'Dibatalkan'}:
        # Buat order_id baru untuk percobaan bayar ulang setelah transaksi lama gagal/expired.
        sale.midtrans_order_id = ''
        sale.midtrans_snap_token = ''
        sale.midtrans_payment_url = ''
        sale.midtrans_status = ''
        sale.midtrans_transaction_id = ''
        sale.save(update_fields=[
            'midtrans_order_id', 'midtrans_snap_token', 'midtrans_payment_url',
            'midtrans_status', 'midtrans_transaction_id'
        ])

    try:
        data = create_snap_transaction(sale, request)
        messages.success(request, 'Link pembayaran Midtrans berhasil dibuat. Pelanggan dapat melanjutkan pembayaran.')
        redirect_url = data.get('redirect_url') or sale.midtrans_payment_url
        if redirect_url:
            return redirect(redirect_url)
    except MidtransError as exc:
        messages.error(request, str(exc))
    return redirect('sales:invoice', pk=sale.pk)


@login_required
@permission_required('sales.invoices')
@require_POST
def check_midtrans_payment(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    try:
        payload = get_transaction_status(sale)
        apply_midtrans_status(sale, payload)
        messages.success(request, f'Status Midtrans diperbarui: {sale.status}.')
    except MidtransError as exc:
        messages.error(request, str(exc))
    return redirect('sales:invoice', pk=sale.pk)


@csrf_exempt
@require_POST
def midtrans_notification(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid JSON')

    if not verify_notification_signature(payload):
        return HttpResponseBadRequest('Invalid signature')

    order_id = payload.get('order_id')
    sale = Sale.objects.filter(midtrans_order_id=order_id).first()
    if not sale:
        return HttpResponseBadRequest('Order ID not found')

    apply_midtrans_status(sale, payload)
    return JsonResponse({'ok': True, 'invoice_no': sale.invoice_no, 'status': sale.status})


@login_required
@permission_required('sales.customers')
def edit_customer(request, pk):
    obj = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        obj.name = request.POST['name']
        obj.phone = request.POST.get('phone','')
        obj.email = request.POST.get('email','')
        obj.address = request.POST.get('address','')
        obj.save()
        return redirect('sales:customers')
    return render(request, 'sales/customer_form.html', {'obj': obj, 'mode': 'edit'})

@login_required
@permission_required('sales.customers')
@require_POST
def delete_customer(request, pk):
    get_object_or_404(Customer, pk=pk).delete()
    return redirect('sales:customers')
