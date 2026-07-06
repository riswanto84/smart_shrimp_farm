from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from django.db.models import Sum
from ponds.models import Pond
from sales.models import Sale
from .models import OperationalExpense
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf, rupiah
from core.utils import parse_rupiah


def _expense_queryset(request):
    date_from, date_to = get_date_range(request)
    items = OperationalExpense.objects.select_related('pond').order_by('-date')
    items = filter_by_date_range(items, 'date', date_from, date_to)
    category = request.GET.get('category') or ''
    pond = request.GET.get('pond') or ''
    if category:
        items = items.filter(category=category)
    if pond:
        items = items.filter(pond_id=pond)
    return items, date_from, date_to


def _expense_rows(items):
    rows = []
    for i in items:
        rows.append([
            i.date.strftime('%d/%m/%Y'),
            i.category,
            i.name,
            i.pond.name if i.pond else 'Semua Kolam',
            rupiah(i.amount),
            i.payment_method,
            i.notes,
        ])
    return rows


@login_required
@permission_required('finance.expenses')
def expenses(request):
    items, date_from, date_to = _expense_queryset(request)
    total = items.aggregate(s=Sum('amount'))['s'] or 0
    ponds = Pond.objects.all()
    return render(request, 'finance/expenses.html', {
        'items': items,
        'total': total,
        'date_from': date_from,
        'date_to': date_to,
        'ponds': ponds,
        'categories': OperationalExpense.CATEGORIES,
    })


@login_required
@permission_required('finance.expenses')
def export_expenses_excel(request):
    items, date_from, date_to = _expense_queryset(request)
    rows = _expense_rows(items)
    total = items.aggregate(s=Sum('amount'))['s'] or 0
    return export_excel(
        'laporan_pengeluaran_operasional',
        'Laporan Pengeluaran Operasional',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kategori', 'Nama Pengeluaran', 'Kolam', 'Jumlah', 'Metode Bayar', 'Catatan'],
        rows,
        [['', '', 'TOTAL', '', rupiah(total), '', '']]
    )


@login_required
@permission_required('finance.expenses')
def export_expenses_pdf(request):
    items, date_from, date_to = _expense_queryset(request)
    rows = _expense_rows(items)
    total = items.aggregate(s=Sum('amount'))['s'] or 0
    pdf_rows = [[r[0], r[1], r[2], r[3], rupiah(r[4]), r[5], r[6]] for r in rows]
    return export_pdf(
        'laporan_pengeluaran_operasional',
        'Laporan Pengeluaran Operasional',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kategori', 'Nama Pengeluaran', 'Kolam', 'Jumlah', 'Metode', 'Catatan'],
        pdf_rows,
        [['', '', 'TOTAL', '', rupiah(total), '', '']]
    )


@login_required
@permission_required('finance.expenses')
def add_expense(request):
    ponds = Pond.objects.all()
    if request.method == 'POST':
        OperationalExpense.objects.create(
            date=request.POST['date'],
            category=request.POST['category'],
            pond_id=request.POST.get('pond') or None,
            name=request.POST['name'],
            amount=parse_rupiah(request.POST.get('amount')), 
            payment_method=request.POST.get('payment_method', 'Cash'),
            receipt=request.FILES.get('receipt'),
            notes=request.POST.get('notes', '')
        )
        return redirect('finance:expenses')
    return render(request, 'finance/expense_form.html', {'ponds': ponds, 'categories': OperationalExpense.CATEGORIES})


def _profit_loss_data(request):
    date_from, date_to = get_date_range(request)
    sales = Sale.objects.all()
    sales = filter_by_date_range(sales, 'date', date_from, date_to, is_datetime=True)
    expenses = OperationalExpense.objects.all()
    expenses = filter_by_date_range(expenses, 'date', date_from, date_to)
    revenue = sales.aggregate(s=Sum('total_amount'))['s'] or 0
    expense_total = expenses.aggregate(s=Sum('amount'))['s'] or 0
    profit = revenue - expense_total
    return date_from, date_to, revenue, expense_total, profit


@login_required
@permission_required('finance.profit_loss')
def profit_loss(request):
    date_from, date_to, revenue, expense_total, profit = _profit_loss_data(request)
    return render(request, 'finance/profit_loss.html', {
        'date_from': date_from,
        'date_to': date_to,
        'revenue': revenue,
        'expense_total': expense_total,
        'profit': profit,
    })


@login_required
@permission_required('finance.profit_loss')
def export_profit_loss_excel(request):
    date_from, date_to, revenue, expense_total, profit = _profit_loss_data(request)
    rows = [
        ['Pendapatan Penjualan', rupiah(revenue)],
        ['Pengeluaran Operasional', rupiah(expense_total)],
        ['Laba/Rugi Bersih', rupiah(profit)],
    ]
    return export_excel('laporan_laba_rugi', 'Laporan Laba Rugi', f'Periode: {format_date_range(date_from, date_to)}', ['Uraian', 'Jumlah'], rows)


@login_required
@permission_required('finance.profit_loss')
def export_profit_loss_pdf(request):
    date_from, date_to, revenue, expense_total, profit = _profit_loss_data(request)
    rows = [
        ['Pendapatan Penjualan', rupiah(revenue)],
        ['Pengeluaran Operasional', rupiah(expense_total)],
        ['Laba/Rugi Bersih', rupiah(profit)],
    ]
    return export_pdf('laporan_laba_rugi', 'Laporan Laba Rugi', f'Periode: {format_date_range(date_from, date_to)}', ['Uraian', 'Jumlah'], rows)
