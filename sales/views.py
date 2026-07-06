from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from django.http import FileResponse
from django.db.models import Sum
from .models import Customer, Sale, SaleItem
from operations.models import Harvest
from .pdf import build_invoice_pdf, safe_invoice_filename
from django.utils import timezone
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf, rupiah
from core.utils import parse_rupiah


@login_required
@permission_required('sales.customers')
def customers(request):
    return render(request, 'sales/customers.html', {'customers': Customer.objects.all()})


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
        weight = parse_rupiah(request.POST.get('weight_kg')); price = parse_rupiah(request.POST.get('price_per_kg')); subtotal = weight * price
        sale = Sale.objects.create(invoice_no=inv, customer_id=request.POST.get('customer') or None, total_kg=weight, total_amount=subtotal, payment_method=request.POST.get('payment_method', 'Cash'), status=request.POST.get('status', 'Lunas'), cashier=request.user, notes=request.POST.get('notes', ''))
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

        weight = parse_rupiah(request.POST.get('weight_kg'))
        price = parse_rupiah(request.POST.get('price_per_kg'))
        subtotal = weight * price

        sale.invoice_no = invoice_no
        sale.customer_id = request.POST.get('customer') or None
        sale.total_kg = weight
        sale.total_amount = subtotal
        sale.payment_method = request.POST.get('payment_method', 'Cash')
        sale.status = request.POST.get('status', 'Lunas')
        sale.notes = request.POST.get('notes', '')
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
    return render(request, 'sales/invoices.html', {'sales': sales, 'date_from': date_from, 'date_to': date_to, 'total': total, 'total_kg': total_kg})


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
