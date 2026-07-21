from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.rbac import permission_required
from django.db.models import Sum, Count, Min, Max
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta
from decimal import Decimal
import json
from ponds.models import Pond
from sales.models import Sale
from .models import OperationalExpense, OperationalExpenseAttachment
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf, rupiah
from core.utils import parse_rupiah
from core.pagination import paginate_queryset
from cultivation.utils import get_selected_cycle, filter_selected_cycle



ALLOWED_EXPENSE_ATTACHMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.docx', '.xlsx'}
MAX_EXPENSE_ATTACHMENT_SIZE = 10 * 1024 * 1024
MAX_EXPENSE_ATTACHMENTS = 20


def _validate_expense_attachments(files, existing_count=0):
    import os
    errors = []
    if existing_count + len(files) > MAX_EXPENSE_ATTACHMENTS:
        errors.append(f'Maksimal {MAX_EXPENSE_ATTACHMENTS} file per transaksi.')
    for upload in files:
        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in ALLOWED_EXPENSE_ATTACHMENT_EXTENSIONS:
            errors.append(f'Format file {upload.name} tidak diizinkan.')
        if upload.size > MAX_EXPENSE_ATTACHMENT_SIZE:
            errors.append(f'Ukuran file {upload.name} melebihi 10 MB.')
    return errors


def _save_expense_attachments(expense, files):
    for upload in files:
        OperationalExpenseAttachment.objects.create(
            expense=expense, file=upload, original_name=upload.name[:255]
        )

def _expense_queryset(request):
    date_from, date_to = get_date_range(request)
    items = filter_selected_cycle(request, OperationalExpense.objects.select_related('pond').prefetch_related('attachments').order_by('-date'))
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
    total = items.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    span = items.aggregate(min_date=Min('date'), max_date=Max('date'))
    if date_from and date_to:
        day_count = max((date_to - date_from).days + 1, 1)
        average_label = 'Rata-rata periode filter'
    elif span['min_date'] and span['max_date']:
        day_count = max((span['max_date'] - span['min_date']).days + 1, 1)
        average_label = 'Rata-rata dari data aktual'
    else:
        day_count = 1
        average_label = 'Belum ada data'
    average_per_day = total / Decimal(day_count)

    top_category = items.values('category').annotate(total_amount=Sum('amount')).order_by('-total_amount').first()
    largest_category = top_category['category'] if top_category else '-'
    largest_category_amount = top_category['total_amount'] if top_category else Decimal('0')

    ponds = Pond.objects.all()
    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'finance/expenses.html', {
        'items': page_obj,
        'page_obj': page_obj,
        'total': total,
        'average_per_day': average_per_day,
        'average_label': average_label,
        'largest_category': largest_category,
        'largest_category_amount': largest_category_amount,
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
        files = request.FILES.getlist('attachments')
        errors = _validate_expense_attachments(files)
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'finance/expense_form.html', {
                'ponds': ponds, 'categories': OperationalExpense.CATEGORIES,
                'form_data': request.POST, 'obj': None, 'mode': 'add',
                'max_files': MAX_EXPENSE_ATTACHMENTS,
            })
        obj = OperationalExpense.objects.create(
            cycle=get_selected_cycle(request, required=True),
            date=request.POST['date'],
            category=request.POST['category'],
            pond_id=request.POST.get('pond') or None,
            name=request.POST['name'],
            amount=parse_rupiah(request.POST.get('amount')),
            payment_method=request.POST.get('payment_method', 'Cash'),
            notes=request.POST.get('notes', '')
        )
        _save_expense_attachments(obj, files)
        messages.success(request, f'Pengeluaran berhasil disimpan dengan {len(files)} lampiran.')
        return redirect('finance:expenses')
    return render(request, 'finance/expense_form.html', {
        'ponds': ponds, 'categories': OperationalExpense.CATEGORIES,
        'form_data': {}, 'obj': None, 'mode': 'add',
        'max_files': MAX_EXPENSE_ATTACHMENTS,
    })


def _profit_loss_data(request):
    date_from, date_to = get_date_range(request)
    sales = filter_selected_cycle(request, Sale.objects.all())
    sales = filter_by_date_range(sales, 'date', date_from, date_to, is_datetime=True)
    expenses = filter_selected_cycle(request, OperationalExpense.objects.all())
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


# -----------------------------------------------------------------------------
# LAPORAN KEUANGAN PERIODIK
# -----------------------------------------------------------------------------

def _decimal(value):
    try:
        return Decimal(value or 0)
    except Exception:
        return Decimal('0')


def _safe_float(value):
    return float(_decimal(value))


def _period_defaults(period_type):
    today = timezone.localdate()
    if period_type == 'monthly':
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
    elif period_type == 'weekly':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period_type == 'daily':
        start = today
        end = today
    else:
        start = today - timedelta(days=30)
        end = today
    return start, end


def _selected_range(request, period_type):
    default_from, default_to = _period_defaults(period_type)
    date_from = parse_date(request.GET.get('date_from') or '') or default_from
    date_to = parse_date(request.GET.get('date_to') or '') or default_to
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _periodic_querysets(request, period_type):
    date_from, date_to = _selected_range(request, period_type)
    pond_id = request.GET.get('pond') or ''
    payment_method = request.GET.get('payment_method') or ''
    status = request.GET.get('status') or ''

    sales = filter_selected_cycle(request, Sale.objects.select_related('customer').prefetch_related('items__harvest__pond').all())
    sales = filter_by_date_range(sales, 'date', date_from, date_to, is_datetime=True)
    if payment_method:
        sales = sales.filter(payment_method=payment_method)
    if status:
        sales = sales.filter(status=status)
    if pond_id:
        sales = sales.filter(items__harvest__pond_id=pond_id).distinct()

    expenses = filter_selected_cycle(request, OperationalExpense.objects.select_related('pond').all())
    expenses = filter_by_date_range(expenses, 'date', date_from, date_to)
    if pond_id:
        expenses = expenses.filter(pond_id=pond_id)

    return sales, expenses, date_from, date_to, pond_id, payment_method, status


def _money_sum(qs, field):
    return _decimal(qs.aggregate(s=Sum(field))['s'])


def _build_series(sales, expenses, period_type, date_from, date_to):
    """Build chart series in Python instead of SQLite date functions.

    The previous implementation used TruncDate/TruncWeek on both DateTimeField
    and DateField. On SQLite this can trigger ``OperationalError: user-defined
    function raised exception`` for the cycle report, especially when a DateField
    is passed through datetime truncation. Grouping in Python is safer and works
    consistently for SQLite, PostgreSQL, and MySQL.
    """
    def normalize_key(value):
        if value is None:
            return None
        if hasattr(value, 'date'):
            value = timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
        if period_type == 'monthly':
            # group by Monday of each week inside the selected month/range
            return value - timedelta(days=value.weekday())
        return value

    def label_for(key):
        if period_type == 'monthly':
            return f"Minggu {key.strftime('%d/%m')}"
        if period_type == 'cycle':
            return key.strftime('%d/%m')
        return key.strftime('%d/%m')

    buckets = {}

    # Do not use .only() here because the base queryset uses select_related('customer').
    # In Django, a field cannot be deferred and traversed with select_related at the same time.
    for sale in sales:
        key = normalize_key(sale.date)
        if not key:
            continue
        buckets.setdefault(key, {'label': label_for(key), 'revenue': Decimal('0'), 'expense': Decimal('0')})
        buckets[key]['revenue'] += _decimal(sale.total_amount)

    for expense in expenses:
        key = normalize_key(expense.date)
        if not key:
            continue
        buckets.setdefault(key, {'label': label_for(key), 'revenue': Decimal('0'), 'expense': Decimal('0')})
        buckets[key]['expense'] += _decimal(expense.amount)

    ordered = [buckets[k] for k in sorted(buckets)]
    return {
        'labels': [i['label'] for i in ordered],
        'revenue': [_safe_float(i['revenue']) for i in ordered],
        'expense': [_safe_float(i['expense']) for i in ordered],
        'profit': [_safe_float(i['revenue'] - i['expense']) for i in ordered],
    }


def _expense_composition(expenses):
    rows = []
    total = _money_sum(expenses, 'amount')
    for row in expenses.values('category').annotate(total=Sum('amount')).order_by('-total'):
        amount = _decimal(row['total'])
        percent = float((amount / total * 100) if total else 0)
        rows.append({'label': row['category'] or 'Lainnya', 'amount': amount, 'percent': percent})
    return rows, total


def _payment_composition(sales):
    rows = []
    total = _money_sum(sales, 'total_amount')
    for row in sales.values('payment_method').annotate(total=Sum('total_amount')).order_by('-total'):
        amount = _decimal(row['total'])
        percent = float((amount / total * 100) if total else 0)
        rows.append({'label': row['payment_method'] or '-', 'amount': amount, 'percent': percent})
    return rows


def _receivables_data(base_sales=None):
    qs = base_sales or Sale.objects.all()
    qs = qs.filter(status__in=['Belum Lunas', 'Menunggu Pembayaran'])
    total = _money_sum(qs, 'total_amount')
    today = timezone.localdate()
    buckets = [
        ('0-7 hari', 0, 7),
        ('8-14 hari', 8, 14),
        ('15-30 hari', 15, 30),
        ('>30 hari', 31, 9999),
    ]
    aging = []
    for label, low, high in buckets:
        amount = Decimal('0')
        count = 0
        for s in qs:
            age = (today - timezone.localtime(s.date).date()).days
            if low <= age <= high:
                amount += _decimal(s.total_amount)
                count += 1
        aging.append({'label': label, 'amount': amount, 'count': count, 'percent': float((amount / total * 100) if total else 0)})

    rows = []
    for s in qs.select_related('customer').order_by('date')[:12]:
        age = (today - timezone.localtime(s.date).date()).days
        if age <= 7:
            badge = 'Belum Jatuh Tempo'
        elif age <= 30:
            badge = f'Terlambat {age} hari'
        else:
            badge = f'Terlambat >30 hari'
        rows.append({'sale': s, 'age': age, 'badge': badge})
    return total, aging, rows


def _financial_report_context(request, period_type=None):
    period_type = period_type or request.GET.get('type') or 'daily'
    if period_type not in {'daily', 'weekly', 'monthly', 'cycle', 'receivable'}:
        period_type = 'daily'

    sales, expenses, date_from, date_to, pond_id, payment_method, status = _periodic_querysets(request, period_type)
    revenue = _money_sum(sales, 'total_amount')
    expense_total = _money_sum(expenses, 'amount')
    profit = revenue - expense_total
    total_kg = _decimal(sales.aggregate(s=Sum('total_kg'))['s'])
    total_transactions = sales.count()
    receivable_total, aging_rows, receivable_rows = _receivables_data(sales if period_type == 'receivable' else None)
    composition, composition_total = _expense_composition(expenses)
    payment_rows = _payment_composition(sales)
    series = _build_series(sales, expenses, period_type, date_from, date_to)

    top_expense = composition[0] if composition else {'label': '-', 'amount': Decimal('0'), 'percent': 0}
    top_sale = sales.order_by('-total_amount').first()
    best_period = None
    if series['labels']:
        profits = series['profit']
        best_idx = profits.index(max(profits))
        best_period = {'label': series['labels'][best_idx], 'amount': Decimal(str(profits[best_idx]))}

    table_rows = []
    if period_type == 'receivable':
        table_rows = receivable_rows
    else:
        for idx, label in enumerate(series['labels']):
            rev = Decimal(str(series['revenue'][idx]))
            exp = Decimal(str(series['expense'][idx]))
            table_rows.append({
                'label': label,
                'revenue': rev,
                'expense': exp,
                'profit': rev - exp,
                'receivable': receivable_total if idx == len(series['labels']) - 1 else Decimal('0'),
            })

    return {
        'period_type': period_type,
        'date_from': date_from,
        'date_to': date_to,
        'pond_id': pond_id,
        'payment_method': payment_method,
        'status': status,
        'ponds': Pond.objects.all().order_by('name'),
        'payment_methods': Sale.PAYMENT,
        'statuses': Sale.STATUS,
        'revenue': revenue,
        'expense_total': expense_total,
        'profit': profit,
        'total_kg': total_kg,
        'total_transactions': total_transactions,
        'receivable_total': receivable_total,
        'composition': composition,
        'payment_rows': payment_rows,
        'aging_rows': aging_rows,
        'receivable_rows': receivable_rows,
        'table_rows': table_rows,
        'top_expense': top_expense,
        'top_sale': top_sale,
        'best_period': best_period,
        'series_json': json.dumps(series),
        'expense_chart_json': json.dumps({
            'labels': [i['label'] for i in composition],
            'values': [_safe_float(i['amount']) for i in composition],
        }),
        'payment_chart_json': json.dumps({
            'labels': [i['label'] for i in payment_rows],
            'values': [_safe_float(i['amount']) for i in payment_rows],
        }),
        'aging_chart_json': json.dumps({
            'labels': [i['label'] for i in aging_rows],
            'values': [_safe_float(i['amount']) for i in aging_rows],
        }),
    }


@login_required
@permission_required('finance.periodic_report')
def periodic_report(request):
    context = _financial_report_context(request)
    return render(request, 'finance/periodic_report.html', context)


@login_required
@permission_required('finance.periodic_report')
def export_periodic_report_excel(request):
    ctx = _financial_report_context(request)
    if ctx['period_type'] == 'receivable':
        headers = ['Pelanggan', 'No Nota', 'Tanggal', 'Nilai Piutang', 'Umur Piutang', 'Status Tagihan']
        rows = [[r['sale'].customer.name if r['sale'].customer else '-', r['sale'].invoice_no, timezone.localtime(r['sale'].date).strftime('%d/%m/%Y'), rupiah(r['sale'].total_amount), f"{r['age']} hari", r['badge']] for r in ctx['receivable_rows']]
        total_rows = [['', '', 'TOTAL', rupiah(ctx['receivable_total']), '', '']]
    else:
        headers = ['Periode', 'Omzet', 'Pengeluaran', 'Laba Bersih', 'Piutang']
        rows = [[r['label'], rupiah(r['revenue']), rupiah(r['expense']), rupiah(r['profit']), rupiah(r['receivable'])] for r in ctx['table_rows']]
        total_rows = [['TOTAL', rupiah(ctx['revenue']), rupiah(ctx['expense_total']), rupiah(ctx['profit']), rupiah(ctx['receivable_total'])]]
    return export_excel('laporan_keuangan_periodik', 'Laporan Keuangan Periodik', f"Periode: {format_date_range(ctx['date_from'], ctx['date_to'])}", headers, rows, total_rows)


def _period_label(period_type):
    return {
        'daily': 'Harian',
        'weekly': 'Mingguan',
        'monthly': 'Bulanan',
        'cycle': 'Per Siklus',
        'receivable': 'Piutang',
    }.get(period_type, 'Periodik')


def _pdf_money(value):
    return rupiah(value).replace('Rp ', 'Rp ')


def _safe_percent(value):
    try:
        return f"{float(value):.1f}%".replace('.', ',')
    except Exception:
        return '0,0%'


def _draw_management_header(canvas, doc, title='Laporan Keuangan Periodik'):
    """Header/footer profesional untuk laporan manajemen."""
    canvas.saveState()
    width, height = doc.pagesize
    navy = colors.HexColor('#082B5A')
    gold = colors.HexColor('#D49A1D')
    light = colors.HexColor('#F5F8FC')

    canvas.setFillColor(navy)
    canvas.rect(0, height - 54, width, 54, stroke=0, fill=1)
    canvas.setFillColor(gold)
    canvas.rect(0, height - 57, width, 3, stroke=0, fill=1)

    logo_path = settings.BASE_DIR / 'static' / 'img' / 'logo_uen_thermal.png'
    if logo_path.exists():
        try:
            canvas.drawImage(str(logo_path), 34, height - 48, width=40, height=32, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 12)
    canvas.drawString(82, height - 26, 'UDANG EMAS NUSANTARA')
    canvas.setFont('Helvetica', 8)
    canvas.drawString(82, height - 39, 'Dari tambak nusantara untuk kualitas dunia')

    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawRightString(width - 34, height - 26, title)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(width - 34, height - 39, timezone.localtime().strftime('Dicetak: %d/%m/%Y %H:%M WIB'))

    canvas.setFillColor(light)
    canvas.rect(0, 0, width, 24, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor('#5B6B82'))
    canvas.setFont('Helvetica', 7)
    canvas.drawString(34, 9, 'Smart Shrimp Farm - Laporan internal manajemen')
    canvas.drawRightString(width - 34, 9, f'Halaman {doc.page}')
    canvas.restoreState()


def _kpi_card(title, value, note, color_hex='#0B3A75'):
    title_style = ParagraphStyle('kpi_title_' + title[:4], fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor('#52637A'), leading=9)
    value_style = ParagraphStyle('kpi_value_' + title[:4], fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor(color_hex), leading=15)
    note_style = ParagraphStyle('kpi_note_' + title[:4], fontName='Helvetica', fontSize=7.2, textColor=colors.HexColor('#6B7A90'), leading=9)
    box = Table([[Paragraph(title, title_style)], [Paragraph(value, value_style)], [Paragraph(note, note_style)]], colWidths=[118])
    box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDE7F3')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return box


def _professional_table(data, widths=None, total_row=False, small=False):
    table = Table(data, repeatRows=1, colWidths=widths)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#082B5A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.6 if small else 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#DDE7F3')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFF')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 7.2 if small else 7.6),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    # align money columns to the right, except first column
    if data and len(data[0]) > 1:
        style.append(('ALIGN', (1, 1), (-1, -1), 'RIGHT'))
    if total_row and len(data) > 1:
        style += [
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EAF2FF')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 0.8, colors.HexColor('#082B5A')),
        ]
    table.setStyle(TableStyle(style))
    return table


def _make_management_insight(ctx):
    revenue = ctx['revenue']
    expense = ctx['expense_total']
    profit = ctx['profit']
    margin = (profit / revenue * 100) if revenue else Decimal('0')
    top_expense = ctx['top_expense']
    receivable = ctx['receivable_total']
    lines = []
    if profit >= 0:
        lines.append(f"Periode ini membukukan laba bersih sebesar <b>{rupiah(profit)}</b> dengan estimasi margin <b>{_safe_percent(margin)}</b> dari omzet.")
    else:
        lines.append(f"Periode ini masih mencatat rugi bersih sebesar <b>{rupiah(abs(profit))}</b>; perlu pengendalian biaya dan percepatan penjualan.")
    if top_expense and top_expense['amount']:
        lines.append(f"Komponen biaya terbesar adalah <b>{top_expense['label']}</b> sebesar <b>{rupiah(top_expense['amount'])}</b> atau <b>{_safe_percent(top_expense['percent'])}</b> dari total pengeluaran.")
    if receivable:
        lines.append(f"Piutang belum lunas yang perlu dipantau sebesar <b>{rupiah(receivable)}</b>.")
    if ctx.get('best_period'):
        lines.append(f"Periode dengan laba tertinggi pada grafik ringkasan adalah <b>{ctx['best_period']['label']}</b> sebesar <b>{rupiah(ctx['best_period']['amount'])}</b>.")
    return lines


@login_required
@permission_required('finance.periodic_report')
def export_periodic_report_pdf(request):
    """Export PDF laporan periodik dengan format manajemen.

    Berbeda dari export_pdf generik, format ini memakai header brand, ringkasan eksekutif,
    KPI, insight, tabel ringkasan, komposisi biaya, metode pembayaran, dan piutang.
    """
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    ctx = _financial_report_context(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_keuangan_periodik_manajemen.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=34,
        leftMargin=34,
        topMargin=76,
        bottomMargin=38,
        title='Laporan Keuangan Periodik Manajemen',
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('MgmtTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#082B5A'), alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('MgmtSubtitle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#52637A'), alignment=TA_CENTER)
    section_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#082B5A'), spaceBefore=8, spaceAfter=6)
    normal_style = ParagraphStyle('MgmtNormal', parent=styles['Normal'], fontSize=8.2, leading=11, textColor=colors.HexColor('#1E293B'))
    small_style = ParagraphStyle('MgmtSmall', parent=styles['Normal'], fontSize=7.4, leading=9, textColor=colors.HexColor('#52637A'))

    elements = []
    period_name = _period_label(ctx['period_type'])
    period_text = format_date_range(ctx['date_from'], ctx['date_to'])

    elements.append(Paragraph('Laporan Keuangan Periodik', title_style))
    elements.append(Paragraph(f'Tipe laporan: <b>{period_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Periode: <b>{period_text}</b>', subtitle_style))
    elements.append(Spacer(1, 12))

    # ringkasan filter
    filter_data = [[
        Paragraph('<b>Filter Kolam</b><br/>' + ('Semua Kolam' if not ctx['pond_id'] else str(ctx['pond_id'])), small_style),
        Paragraph('<b>Metode Pembayaran</b><br/>' + (ctx['payment_method'] or 'Semua Metode'), small_style),
        Paragraph('<b>Status Nota</b><br/>' + (ctx['status'] or 'Semua Status'), small_style),
        Paragraph('<b>Total Transaksi</b><br/>' + str(ctx['total_transactions']), small_style),
    ]]
    filter_table = Table(filter_data, colWidths=[185, 185, 185, 185])
    filter_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F8FC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDE7F3')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#DDE7F3')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(filter_table)
    elements.append(Spacer(1, 10))

    # KPI cards
    margin = (ctx['profit'] / ctx['revenue'] * 100) if ctx['revenue'] else Decimal('0')
    kpis = [[
        _kpi_card('Total Omzet', rupiah(ctx['revenue']), f"Volume: {ctx['total_kg']} kg", '#0B67E9'),
        _kpi_card('Total Pengeluaran', rupiah(ctx['expense_total']), 'Biaya operasional periode ini', '#F59E0B'),
        _kpi_card('Laba Bersih', rupiah(ctx['profit']), f"Margin: {_safe_percent(margin)}", '#0F8A4B' if ctx['profit'] >= 0 else '#DC2626'),
        _kpi_card('Piutang Belum Lunas', rupiah(ctx['receivable_total']), 'Nota belum/menunggu lunas', '#6D4CD9'),
    ]]
    kpi_table = Table(kpis, colWidths=[185, 185, 185, 185])
    kpi_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 8)]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph('Ringkasan Eksekutif', section_style))
    insight_lines = _make_management_insight(ctx)
    insight_data = [[Paragraph('• ' + line, normal_style)] for line in insight_lines]
    insight_table = Table(insight_data, colWidths=[750])
    insight_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF8E7')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#F4D08B')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(insight_table)
    elements.append(Spacer(1, 10))

    # Tabel utama
    if ctx['period_type'] == 'receivable':
        elements.append(Paragraph('Daftar Piutang Pelanggan', section_style))
        main_data = [['Pelanggan', 'No Nota', 'Tanggal', 'Nilai Piutang', 'Umur', 'Status Tagihan']]
        for r in ctx['receivable_rows']:
            sale = r['sale']
            main_data.append([
                sale.customer.name if sale.customer else '-',
                sale.invoice_no,
                timezone.localtime(sale.date).strftime('%d/%m/%Y'),
                rupiah(sale.total_amount),
                f"{r['age']} hari",
                r['badge'],
            ])
        main_data.append(['TOTAL', '', '', rupiah(ctx['receivable_total']), '', ''])
        elements.append(_professional_table(main_data, widths=[160, 120, 80, 110, 70, 140], total_row=True))
    else:
        elements.append(Paragraph('Ringkasan Periode', section_style))
        main_data = [['Periode', 'Omzet', 'Pengeluaran', 'Laba Bersih', 'Piutang']]
        for r in ctx['table_rows']:
            main_data.append([r['label'], rupiah(r['revenue']), rupiah(r['expense']), rupiah(r['profit']), rupiah(r['receivable'])])
        main_data.append(['TOTAL', rupiah(ctx['revenue']), rupiah(ctx['expense_total']), rupiah(ctx['profit']), rupiah(ctx['receivable_total'])])
        elements.append(_professional_table(main_data, widths=[155, 145, 145, 145, 145], total_row=True))

    elements.append(Spacer(1, 12))

    # Dua tabel analisis tambahan berdampingan
    composition_data = [['Komponen Biaya', 'Jumlah', '%']]
    for item in ctx['composition'][:8]:
        composition_data.append([item['label'], rupiah(item['amount']), _safe_percent(item['percent'])])
    if len(composition_data) == 1:
        composition_data.append(['Tidak ada data', 'Rp 0', '0,0%'])

    payment_data = [['Metode Bayar', 'Jumlah', '%']]
    for item in ctx['payment_rows'][:8]:
        payment_data.append([item['label'], rupiah(item['amount']), _safe_percent(item['percent'])])
    if len(payment_data) == 1:
        payment_data.append(['Tidak ada data', 'Rp 0', '0,0%'])

    left_block = [Paragraph('Komposisi Pengeluaran', section_style), _professional_table(composition_data, widths=[130, 100, 55], small=True)]
    right_block = [Paragraph('Distribusi Metode Pembayaran', section_style), _professional_table(payment_data, widths=[130, 100, 55], small=True)]
    extra = Table([[left_block, right_block]], colWidths=[365, 365])
    extra.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 14)]))
    elements.append(extra)

    elements.append(Spacer(1, 12))
    elements.append(Paragraph('Catatan Manajemen', section_style))
    notes = [
        'Laporan ini disusun otomatis berdasarkan data penjualan, pengeluaran operasional, dan status pembayaran yang tercatat pada aplikasi.',
        'Angka laba bersih merupakan selisih omzet dan pengeluaran operasional periode terpilih; belum memperhitungkan penyusutan aset, pajak, dan koreksi akuntansi lain jika belum dicatat pada sistem.',
        'Piutang perlu ditindaklanjuti secara berkala terutama nota dengan umur lebih dari 14 hari.',
    ]
    notes_data = [[Paragraph('• ' + n, small_style)] for n in notes]
    notes_table = Table(notes_data, colWidths=[750])
    notes_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F8FC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDE7F3')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(notes_table)

    doc.build(elements, onFirstPage=_draw_management_header, onLaterPages=_draw_management_header)
    return response


@login_required
@permission_required('finance.expenses')
def edit_expense(request, pk):
    obj = get_object_or_404(OperationalExpense, pk=pk)
    ponds = Pond.objects.all()
    if request.method == 'POST':
        files = request.FILES.getlist('attachments')
        errors = _validate_expense_attachments(files, obj.attachments.count())
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'finance/expense_form.html', {
                'ponds': ponds, 'categories': OperationalExpense.CATEGORIES,
                'obj': obj, 'mode': 'edit', 'max_files': MAX_EXPENSE_ATTACHMENTS,
            })
        obj.cycle = get_selected_cycle(request, required=True)
        obj.date = request.POST['date']
        obj.category = request.POST['category']
        obj.pond_id = request.POST.get('pond') or None
        obj.name = request.POST['name']
        obj.amount = parse_rupiah(request.POST.get('amount'))
        obj.payment_method = request.POST.get('payment_method', 'Cash')
        obj.notes = request.POST.get('notes', '')
        obj.save()
        _save_expense_attachments(obj, files)
        messages.success(request, f'Pengeluaran diperbarui. {len(files)} lampiran baru ditambahkan.')
        return redirect('finance:expenses')
    return render(request, 'finance/expense_form.html', {
        'ponds': ponds, 'categories': OperationalExpense.CATEGORIES,
        'obj': obj, 'mode': 'edit', 'max_files': MAX_EXPENSE_ATTACHMENTS,
    })

@login_required
@permission_required('finance.expenses')
@require_POST
def delete_expense_attachment(request, pk):
    attachment = get_object_or_404(OperationalExpenseAttachment, pk=pk)
    expense_id = attachment.expense_id
    if attachment.file:
        attachment.file.delete(save=False)
    attachment.delete()
    messages.success(request, 'Lampiran berhasil dihapus.')
    return redirect('finance:edit_expense', pk=expense_id)


@login_required
@permission_required('finance.expenses')
@require_POST
def delete_expense(request, pk):
    get_object_or_404(OperationalExpense, pk=pk).delete()
    return redirect('finance:expenses')

# =============================================================================
# MODUL KEUANGAN & PAJAK RINGKAS
# Neraca, laba rugi, peredaran bruto, aset dan penyusutan
# =============================================================================
from calendar import monthrange
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from .models import OtherRevenue, BalanceEntry, FixedAsset, TradeAccount, TradePayment


def _as_date(request):
    return parse_date(request.GET.get('as_of') or '') or timezone.localdate()


def _date_period(request):
    year = int(request.GET.get('year') or timezone.localdate().year)
    date_from = parse_date(request.GET.get('date_from') or '') or timezone.datetime(year, 1, 1).date()
    date_to = parse_date(request.GET.get('date_to') or '') or timezone.datetime(year, 12, 31).date()
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _fiscal_life(group):
    return {
        'group_1': 4,
        'group_2': 8,
        'group_3': 16,
        'group_4': 20,
        'permanent_building': 20,
        'non_permanent_building': 10,
    }.get(group)


def _months_used(asset, as_of):
    if asset.use_date > as_of or asset.fiscal_group == 'non_depreciable':
        return 0
    months = (as_of.year - asset.use_date.year) * 12 + as_of.month - asset.use_date.month + 1
    life = _fiscal_life(asset.fiscal_group)
    if life:
        months = min(months, life * 12)
    return max(months, 0)


def _asset_depreciation(asset, as_of):
    cost = asset.total_cost
    life = _fiscal_life(asset.fiscal_group)
    if not life or asset.fiscal_group == 'non_depreciable':
        annual = Decimal('0')
        accumulated = Decimal('0')
    else:
        depreciable = max(cost - (asset.residual_value or Decimal('0')), Decimal('0'))
        annual = depreciable / Decimal(life)
        accumulated = min((annual / Decimal('12')) * Decimal(_months_used(asset, as_of)), depreciable)
    return {
        'annual': annual,
        'accumulated': accumulated,
        'book_value': max(cost - accumulated, Decimal('0')),
        'life': life,
    }


def _gross_turnover_data(request):
    date_from, date_to = _date_period(request)
    sales = Sale.objects.filter(date__date__range=(date_from, date_to)).exclude(status__in=['Gagal','Expired','Dibatalkan','Refund'])
    other = OtherRevenue.objects.filter(date__range=(date_from, date_to))
    rows = []
    for item in sales.select_related('customer').order_by('date'):
        rows.append({'date': item.date.date(), 'document': item.invoice_no, 'customer': item.customer.name if item.customer else '-', 'source': 'Penjualan Udang', 'amount': item.total_amount, 'kind': 'sale'})
    for item in other.order_by('date'):
        rows.append({'date': item.date, 'document': item.document_number or '-', 'customer': item.customer or '-', 'source': item.revenue_type, 'amount': item.gross_amount, 'kind': 'other'})
    rows.sort(key=lambda r: r['date'])
    total = sum((r['amount'] for r in rows), Decimal('0'))
    monthly = []
    for month in range(1,13):
        value = sum((r['amount'] for r in rows if r['date'].year == date_from.year and r['date'].month == month), Decimal('0'))
        monthly.append({'month': month, 'label': timezone.datetime(2000,month,1).strftime('%B'), 'amount': value})
    return date_from, date_to, rows, total, monthly


@login_required
@permission_required('finance.tax_reports')
def tax_dashboard(request):
    date_from, date_to = _date_period(request)
    _, _, _, turnover, _ = _gross_turnover_data(request)
    expenses = OperationalExpense.objects.filter(date__range=(date_from,date_to))
    expense_total = expenses.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    fiscal_expense = expenses.filter(is_fiscal_deductible=True).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    assets = FixedAsset.objects.filter(status='active')
    asset_total = sum((a.total_cost for a in assets), Decimal('0'))
    receivable_total = sum((x.outstanding_amount for x in TradeAccount.objects.filter(account_type=TradeAccount.RECEIVABLE)), Decimal('0'))
    payable_total = sum((x.outstanding_amount for x in TradeAccount.objects.filter(account_type=TradeAccount.PAYABLE)), Decimal('0'))
    overdue_receivable = sum((x.outstanding_amount for x in TradeAccount.objects.filter(account_type=TradeAccount.RECEIVABLE, due_date__lt=timezone.localdate())), Decimal('0'))
    overdue_payable = sum((x.outstanding_amount for x in TradeAccount.objects.filter(account_type=TradeAccount.PAYABLE, due_date__lt=timezone.localdate())), Decimal('0'))
    return render(request,'finance/tax_dashboard.html',{
        'date_from':date_from,'date_to':date_to,'turnover':turnover,'expense_total':expense_total,
        'fiscal_expense':fiscal_expense,'commercial_profit':turnover-expense_total,
        'fiscal_profit_before_adjustment':turnover-fiscal_expense,'asset_total':asset_total,'asset_count':assets.count(),
        'receivable_total':receivable_total,'payable_total':payable_total,
        'overdue_receivable':overdue_receivable,'overdue_payable':overdue_payable,
    })


@login_required
@permission_required('finance.tax_reports')
def gross_turnover(request):
    date_from,date_to,rows,total,monthly=_gross_turnover_data(request)
    return render(request,'finance/gross_turnover.html',{'date_from':date_from,'date_to':date_to,'rows':rows,'total':total,'monthly':monthly})


@login_required
@permission_required('finance.tax_reports')
def add_other_revenue(request):
    if request.method == 'POST':
        OtherRevenue.objects.create(
            cycle=get_selected_cycle(request), date=request.POST['date'], document_number=request.POST.get('document_number',''),
            revenue_type=request.POST['revenue_type'], description=request.POST['description'], customer=request.POST.get('customer',''),
            gross_amount=parse_rupiah(request.POST.get('gross_amount')), tax_amount=parse_rupiah(request.POST.get('tax_amount')),
            payment_method=request.POST.get('payment_method','Transfer'), notes=request.POST.get('notes',''))
        messages.success(request,'Pendapatan lain berhasil disimpan.')
        return redirect('finance:gross_turnover')
    return render(request,'finance/other_revenue_form.html',{'types':OtherRevenue.REVENUE_TYPES})


@login_required
@permission_required('finance.tax_reports')
def export_gross_turnover_excel(request):
    date_from,date_to,rows,total,_=_gross_turnover_data(request)
    data=[[r['date'].strftime('%d/%m/%Y'),r['document'],r['customer'],r['source'],rupiah(r['amount'])] for r in rows]
    return export_excel('peredaran_bruto','Laporan Peredaran Bruto',f'Periode: {format_date_range(date_from,date_to)}',['Tanggal','Nomor Bukti','Pelanggan','Sumber Pendapatan','Peredaran Bruto'],data,[['','','','TOTAL',rupiah(total)]])


@login_required
@permission_required('finance.tax_reports')
def export_gross_turnover_pdf(request):
    date_from,date_to,rows,total,_=_gross_turnover_data(request)
    data=[[r['date'].strftime('%d/%m/%Y'),r['document'],r['customer'],r['source'],rupiah(r['amount'])] for r in rows]
    return export_pdf('peredaran_bruto','Laporan Peredaran Bruto',f'Periode: {format_date_range(date_from,date_to)}',['Tanggal','Nomor Bukti','Pelanggan','Sumber Pendapatan','Peredaran Bruto'],data,[['','','','TOTAL',rupiah(total)]])


def _profit_loss_tax_data(request):
    date_from,date_to=_date_period(request)
    _,_,_,revenue,_=_gross_turnover_data(request)
    expenses=OperationalExpense.objects.filter(date__range=(date_from,date_to))
    grouped=list(expenses.values('category').annotate(total=Sum('amount')).order_by('category'))
    expense_total=sum((x['total'] for x in grouped),Decimal('0'))
    non_deductible=expenses.filter(is_fiscal_deductible=False).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    return date_from,date_to,revenue,grouped,expense_total,revenue-expense_total,non_deductible


@login_required
@permission_required('finance.tax_reports')
def tax_profit_loss(request):
    date_from,date_to,revenue,grouped,expense_total,profit,non_deductible=_profit_loss_tax_data(request)
    return render(request,'finance/tax_profit_loss.html',locals())


@login_required
@permission_required('finance.tax_reports')
def export_tax_profit_loss_pdf(request):
    date_from,date_to,revenue,grouped,expense_total,profit,non_deductible=_profit_loss_tax_data(request)
    rows=[['Peredaran Bruto',rupiah(revenue)]]+[[f"Beban {x['category']}",rupiah(x['total'])] for x in grouped]+[['Total Beban',rupiah(expense_total)],['Laba/Rugi Bersih',rupiah(profit)],['Biaya Non-Deductible (informasi)',rupiah(non_deductible)]]
    return export_pdf('laba_rugi_pajak','Laporan Laba Rugi',f'Periode: {format_date_range(date_from,date_to)}',['Uraian','Jumlah'],rows)


@login_required
@permission_required('finance.tax_reports')
def balance_entries(request):
    as_of=_as_date(request)
    entries=BalanceEntry.objects.filter(as_of_date__lte=as_of)
    return render(request,'finance/balance_entries.html',{'entries':entries,'as_of':as_of})


@login_required
@permission_required('finance.tax_reports')
def add_balance_entry(request):
    if request.method=='POST':
        BalanceEntry.objects.create(as_of_date=request.POST['as_of_date'],account_type=request.POST['account_type'],group=request.POST['group'],account_name=request.POST['account_name'],amount=parse_rupiah(request.POST.get('amount')),notes=request.POST.get('notes',''))
        messages.success(request,'Pos neraca berhasil disimpan.')
        return redirect('finance:balance_entries')
    return render(request,'finance/balance_form.html',{'account_types':BalanceEntry.ACCOUNT_TYPES,'asset_groups':BalanceEntry.ASSET_GROUPS,'liability_groups':BalanceEntry.LIABILITY_GROUPS,'equity_groups':BalanceEntry.EQUITY_GROUPS})


def _balance_sheet_data(request):
    as_of=_as_date(request)
    latest={}
    for e in BalanceEntry.objects.filter(as_of_date__lte=as_of).order_by('account_name','-as_of_date','-id'):
        latest.setdefault((e.account_type,e.account_name),e)
    entries=list(latest.values())
    # Piutang dan utang usaha berasal otomatis dari modul kartu utang/piutang.
    # Pos manual dengan kelompok yang sama dikeluarkan agar tidak terjadi hitung ganda.
    assets=[e for e in entries if e.account_type=='asset' and e.group not in ('Aset Tetap','Piutang Usaha')]
    liabilities=[e for e in entries if e.account_type=='liability' and e.group!='Utang Usaha']
    equities=[e for e in entries if e.account_type=='equity']
    def outstanding_as_of(account):
        paid = account.payments.filter(payment_date__lte=as_of).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        return max(account.original_amount - paid, Decimal('0'))
    receivable_total=sum((outstanding_as_of(x) for x in TradeAccount.objects.filter(account_type=TradeAccount.RECEIVABLE, transaction_date__lte=as_of)),Decimal('0'))
    payable_total=sum((outstanding_as_of(x) for x in TradeAccount.objects.filter(account_type=TradeAccount.PAYABLE, transaction_date__lte=as_of)),Decimal('0'))
    fixed_assets=[]
    for a in FixedAsset.objects.filter(use_date__lte=as_of).exclude(status='disposed'):
        dep=_asset_depreciation(a,as_of)
        fixed_assets.append({'asset':a,**dep})
    fixed_cost=sum((x['asset'].total_cost for x in fixed_assets),Decimal('0'))
    accumulated=sum((x['accumulated'] for x in fixed_assets),Decimal('0'))
    total_assets=sum((e.amount for e in assets),Decimal('0'))+receivable_total+fixed_cost-accumulated
    total_liabilities=sum((e.amount for e in liabilities),Decimal('0'))+payable_total
    total_equity=sum((e.amount for e in equities),Decimal('0'))
    start=timezone.datetime(as_of.year,1,1).date()
    mock=type('R',(),{'GET':{'date_from':start.isoformat(),'date_to':as_of.isoformat()}})()
    # laba berjalan dihitung langsung tanpa mengubah request asli
    sales=Sale.objects.filter(date__date__range=(start,as_of)).exclude(status__in=['Gagal','Expired','Dibatalkan','Refund']).aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
    other=OtherRevenue.objects.filter(date__range=(start,as_of)).aggregate(s=Sum('gross_amount'))['s'] or Decimal('0')
    costs=OperationalExpense.objects.filter(date__range=(start,as_of)).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    current_profit=sales+other-costs
    total_equity_with_profit=total_equity+current_profit
    return {'as_of':as_of,'assets':assets,'liabilities':liabilities,'equities':equities,'fixed_assets':fixed_assets,'receivable_total':receivable_total,'payable_total':payable_total,'fixed_cost':fixed_cost,'accumulated':accumulated,'total_assets':total_assets,'total_liabilities':total_liabilities,'total_equity':total_equity,'current_profit':current_profit,'total_equity_with_profit':total_equity_with_profit,'difference':total_assets-total_liabilities-total_equity_with_profit}


@login_required
@permission_required('finance.tax_reports')
def balance_sheet(request):
    return render(request,'finance/balance_sheet.html',_balance_sheet_data(request))


@login_required
@permission_required('finance.tax_reports')
def export_balance_sheet_pdf(request):
    d=_balance_sheet_data(request)
    rows=[]
    for e in d['assets']: rows.append([f"ASET - {e.account_name}",rupiah(e.amount)])
    rows.append(['ASET - Piutang Usaha',rupiah(d['receivable_total'])])
    rows += [['Aset Tetap - Harga Perolehan',rupiah(d['fixed_cost'])],['Akumulasi Penyusutan',f"({rupiah(d['accumulated'])})"],['TOTAL ASET',rupiah(d['total_assets'])]]
    for e in d['liabilities']: rows.append([f"KEWAJIBAN - {e.account_name}",rupiah(e.amount)])
    rows.append(['KEWAJIBAN - Utang Usaha',rupiah(d['payable_total'])])
    rows.append(['TOTAL KEWAJIBAN',rupiah(d['total_liabilities'])])
    for e in d['equities']: rows.append([f"EKUITAS - {e.account_name}",rupiah(e.amount)])
    rows += [['Laba/Rugi Tahun Berjalan',rupiah(d['current_profit'])],['TOTAL EKUITAS',rupiah(d['total_equity_with_profit'])],['SELISIH NERACA',rupiah(d['difference'])]]
    return export_pdf('neraca','Laporan Neraca',f"Posisi per {d['as_of'].strftime('%d/%m/%Y')}",['Uraian','Jumlah'],rows)


@login_required
@permission_required('finance.tax_reports')
def assets(request):
    as_of=_as_date(request)
    rows=[]
    for a in FixedAsset.objects.all(): rows.append({'asset':a,**_asset_depreciation(a,as_of)})
    return render(request,'finance/assets.html',{'rows':rows,'as_of':as_of})


@login_required
@permission_required('finance.tax_reports')
def add_asset(request):
    if request.method=='POST':
        FixedAsset.objects.create(code=request.POST['code'],name=request.POST['name'],category=request.POST['category'],acquisition_date=request.POST['acquisition_date'],use_date=request.POST['use_date'],acquisition_cost=parse_rupiah(request.POST.get('acquisition_cost')),additional_cost=parse_rupiah(request.POST.get('additional_cost')),residual_value=parse_rupiah(request.POST.get('residual_value')),commercial_useful_life_years=int(request.POST.get('commercial_useful_life_years') or 4),fiscal_group=request.POST['fiscal_group'],location=request.POST.get('location',''),document_number=request.POST.get('document_number',''),source_of_funds=request.POST.get('source_of_funds',''),status=request.POST.get('status','active'),notes=request.POST.get('notes',''))
        messages.success(request,'Aset berhasil disimpan.')
        return redirect('finance:assets')
    return render(request,'finance/asset_form.html',{'groups':FixedAsset.FISCAL_GROUPS,'statuses':FixedAsset.STATUS})


@login_required
@permission_required('finance.tax_reports')
def edit_asset(request,pk):
    asset=get_object_or_404(FixedAsset,pk=pk)
    if request.method=='POST':
        for field in ['code','name','category','acquisition_date','use_date','fiscal_group','location','document_number','source_of_funds','status','notes']:
            setattr(asset,field,request.POST.get(field,''))
        asset.acquisition_cost=parse_rupiah(request.POST.get('acquisition_cost')); asset.additional_cost=parse_rupiah(request.POST.get('additional_cost')); asset.residual_value=parse_rupiah(request.POST.get('residual_value')); asset.commercial_useful_life_years=int(request.POST.get('commercial_useful_life_years') or 4); asset.save()
        messages.success(request,'Aset berhasil diperbarui.')
        return redirect('finance:assets')
    return render(request,'finance/asset_form.html',{'asset':asset,'groups':FixedAsset.FISCAL_GROUPS,'statuses':FixedAsset.STATUS})


@login_required
@permission_required('finance.tax_reports')
def depreciation_report(request):
    as_of=_as_date(request); year=as_of.year; rows=[]
    total_cost=total_year=total_accumulated=total_book=Decimal('0')
    for a in FixedAsset.objects.exclude(status='disposed'):
        dep=_asset_depreciation(a,as_of)
        year_start=timezone.datetime(year,1,1).date()
        before=_asset_depreciation(a,year_start-timedelta(days=1))['accumulated']
        current=max(dep['accumulated']-before,Decimal('0'))
        row={'asset':a,**dep,'current_year':current}; rows.append(row)
        total_cost+=a.total_cost; total_year+=current; total_accumulated+=dep['accumulated']; total_book+=dep['book_value']
    return render(request,'finance/depreciation.html',locals())


@login_required
@permission_required('finance.tax_reports')
def export_depreciation_pdf(request):
    as_of=_as_date(request); rows=[]; tc=ta=tb=Decimal('0')
    for a in FixedAsset.objects.exclude(status='disposed'):
        d=_asset_depreciation(a,as_of); tc+=a.total_cost; ta+=d['accumulated']; tb+=d['book_value']; rows.append([a.code,a.name,a.get_fiscal_group_display(),rupiah(a.total_cost),rupiah(d['annual']),rupiah(d['accumulated']),rupiah(d['book_value'])])
    return export_pdf('daftar_aset_penyusutan','Daftar Aset dan Penyusutan Fiskal',f"Posisi per {as_of.strftime('%d/%m/%Y')}",['Kode','Nama Aset','Kelompok','Perolehan','Penyusutan/Tahun','Akumulasi','Nilai Buku'],rows,[['','','TOTAL',rupiah(tc),'',rupiah(ta),rupiah(tb)]])

# =============================================================================
# UTANG DAN PIUTANG USAHA
# =============================================================================
from django.db import transaction


def _trade_queryset(request, account_type):
    items = TradeAccount.objects.filter(account_type=account_type).prefetch_related('payments')
    q = (request.GET.get('q') or '').strip()
    status = request.GET.get('status') or ''
    if q:
        items = items.filter(Q(partner_name__icontains=q) | Q(document_number__icontains=q) | Q(description__icontains=q))
    today = timezone.localdate()
    rows = []
    for item in items:
        if status == 'open' and item.outstanding_amount <= 0:
            continue
        if status == 'paid' and item.outstanding_amount > 0:
            continue
        if status == 'overdue' and not item.is_overdue:
            continue
        age_days = max((today - item.due_date).days, 0) if item.outstanding_amount > 0 else 0
        bucket = 'Belum jatuh tempo'
        if age_days:
            if age_days <= 30: bucket = '1–30 hari'
            elif age_days <= 60: bucket = '31–60 hari'
            elif age_days <= 90: bucket = '61–90 hari'
            else: bucket = '> 90 hari'
        rows.append({'item': item, 'paid': item.paid_amount, 'outstanding': item.outstanding_amount, 'age_days': age_days, 'bucket': bucket})
    return rows


def _trade_summary(rows):
    original = sum((r['item'].original_amount for r in rows), Decimal('0'))
    paid = sum((r['paid'] for r in rows), Decimal('0'))
    outstanding = sum((r['outstanding'] for r in rows), Decimal('0'))
    overdue = sum((r['outstanding'] for r in rows if r['item'].is_overdue), Decimal('0'))
    return original, paid, outstanding, overdue


@login_required
@permission_required('finance.tax_reports')
def receivables(request):
    rows = _trade_queryset(request, TradeAccount.RECEIVABLE)
    original, paid, outstanding, overdue = _trade_summary(rows)
    return render(request, 'finance/trade_accounts.html', {
        'rows': rows, 'account_type': TradeAccount.RECEIVABLE, 'title': 'Piutang Usaha',
        'partner_label': 'Pelanggan', 'original': original, 'paid': paid,
        'outstanding': outstanding, 'overdue': overdue,
    })


@login_required
@permission_required('finance.tax_reports')
def payables(request):
    rows = _trade_queryset(request, TradeAccount.PAYABLE)
    original, paid, outstanding, overdue = _trade_summary(rows)
    return render(request, 'finance/trade_accounts.html', {
        'rows': rows, 'account_type': TradeAccount.PAYABLE, 'title': 'Utang Usaha',
        'partner_label': 'Supplier/Pemasok', 'original': original, 'paid': paid,
        'outstanding': outstanding, 'overdue': overdue,
    })


@login_required
@permission_required('finance.tax_reports')
def add_trade_account(request, account_type):
    if account_type not in {TradeAccount.RECEIVABLE, TradeAccount.PAYABLE}:
        return redirect('finance:tax_dashboard')
    if request.method == 'POST':
        amount = parse_rupiah(request.POST.get('original_amount'))
        transaction_date = parse_date(request.POST.get('transaction_date') or '')
        due_date = parse_date(request.POST.get('due_date') or '')
        if amount <= 0 or not transaction_date or not due_date:
            messages.error(request, 'Tanggal dan nilai transaksi wajib diisi dengan benar.')
        elif due_date < transaction_date:
            messages.error(request, 'Tanggal jatuh tempo tidak boleh sebelum tanggal transaksi.')
        else:
            obj = TradeAccount.objects.create(
                cycle=get_selected_cycle(request), account_type=account_type,
                transaction_date=transaction_date, due_date=due_date,
                document_number=request.POST.get('document_number','').strip(),
                partner_name=request.POST.get('partner_name','').strip(),
                description=request.POST.get('description','').strip(),
                original_amount=amount, notes=request.POST.get('notes','').strip(),
            )
            messages.success(request, f'{obj.get_account_type_display()} berhasil disimpan.')
            return redirect('finance:trade_detail', pk=obj.pk)
    return render(request, 'finance/trade_account_form.html', {
        'account_type': account_type,
        'title': 'Tambah Piutang Usaha' if account_type == TradeAccount.RECEIVABLE else 'Tambah Utang Usaha',
        'partner_label': 'Pelanggan' if account_type == TradeAccount.RECEIVABLE else 'Supplier/Pemasok',
    })


@login_required
@permission_required('finance.tax_reports')
def edit_trade_account(request, pk):
    obj = get_object_or_404(TradeAccount, pk=pk)
    if request.method == 'POST':
        amount = parse_rupiah(request.POST.get('original_amount'))
        transaction_date = parse_date(request.POST.get('transaction_date') or '')
        due_date = parse_date(request.POST.get('due_date') or '')
        if amount < obj.paid_amount:
            messages.error(request, 'Nilai awal tidak boleh lebih kecil dari total pembayaran yang sudah dicatat.')
        elif not transaction_date or not due_date or due_date < transaction_date:
            messages.error(request, 'Periksa kembali tanggal transaksi dan jatuh tempo.')
        else:
            obj.transaction_date=transaction_date; obj.due_date=due_date
            obj.document_number=request.POST.get('document_number','').strip()
            obj.partner_name=request.POST.get('partner_name','').strip()
            obj.description=request.POST.get('description','').strip()
            obj.original_amount=amount; obj.notes=request.POST.get('notes','').strip(); obj.save()
            messages.success(request, 'Data berhasil diperbarui.')
            return redirect('finance:trade_detail', pk=obj.pk)
    return render(request, 'finance/trade_account_form.html', {
        'obj':obj, 'account_type':obj.account_type,
        'title':'Edit '+obj.get_account_type_display(),
        'partner_label':'Pelanggan' if obj.account_type == TradeAccount.RECEIVABLE else 'Supplier/Pemasok',
    })


@login_required
@permission_required('finance.tax_reports')
def trade_detail(request, pk):
    obj = get_object_or_404(TradeAccount.objects.prefetch_related('payments'), pk=pk)
    return render(request, 'finance/trade_account_detail.html', {
        'obj':obj, 'payments':obj.payments.all(), 'paid':obj.paid_amount,
        'outstanding':obj.outstanding_amount,
    })


@login_required
@permission_required('finance.tax_reports')
@require_POST
@transaction.atomic
def add_trade_payment(request, pk):
    obj = get_object_or_404(TradeAccount.objects.select_for_update(), pk=pk)
    amount = parse_rupiah(request.POST.get('amount'))
    payment_date = parse_date(request.POST.get('payment_date') or '')
    if not payment_date or amount <= 0:
        messages.error(request, 'Tanggal dan jumlah pembayaran wajib diisi.')
    elif amount > obj.outstanding_amount:
        messages.error(request, 'Pembayaran tidak boleh melebihi sisa saldo.')
    else:
        TradePayment.objects.create(
            trade_account=obj, payment_date=payment_date, amount=amount,
            payment_method=request.POST.get('payment_method','Transfer'),
            document_number=request.POST.get('document_number','').strip(),
            notes=request.POST.get('notes','').strip(),
        )
        messages.success(request, 'Pembayaran berhasil dicatat.')
    return redirect('finance:trade_detail', pk=obj.pk)


@login_required
@permission_required('finance.tax_reports')
@require_POST
def delete_trade_payment(request, pk):
    payment = get_object_or_404(TradePayment, pk=pk)
    account_pk = payment.trade_account_id
    payment.delete()
    messages.success(request, 'Pembayaran berhasil dihapus.')
    return redirect('finance:trade_detail', pk=account_pk)


@login_required
@permission_required('finance.tax_reports')
@require_POST
def delete_trade_account(request, pk):
    obj = get_object_or_404(TradeAccount, pk=pk)
    target = 'finance:receivables' if obj.account_type == TradeAccount.RECEIVABLE else 'finance:payables'
    obj.delete()
    messages.success(request, 'Data utang/piutang berhasil dihapus.')
    return redirect(target)


@login_required
@permission_required('finance.tax_reports')
def export_trade_pdf(request, account_type):
    if account_type not in {TradeAccount.RECEIVABLE, TradeAccount.PAYABLE}:
        return redirect('finance:tax_dashboard')
    rows = _trade_queryset(request, account_type)
    title = 'Daftar Piutang Usaha' if account_type == TradeAccount.RECEIVABLE else 'Daftar Utang Usaha'
    data = [[
        r['item'].transaction_date.strftime('%d/%m/%Y'), r['item'].due_date.strftime('%d/%m/%Y'),
        r['item'].document_number or '-', r['item'].partner_name, r['item'].description,
        rupiah(r['item'].original_amount), rupiah(r['paid']), rupiah(r['outstanding']),
        ('Jatuh tempo' if r['item'].is_overdue else r['item'].payment_status)
    ] for r in rows]
    totals = _trade_summary(rows)
    return export_pdf(
        'piutang_usaha' if account_type == TradeAccount.RECEIVABLE else 'utang_usaha', title,
        f'Posisi per {timezone.localdate().strftime("%d/%m/%Y")}',
        ['Transaksi','Jatuh Tempo','Dokumen','Mitra','Uraian','Nilai Awal','Dibayar','Saldo','Status'],
        data, [['','','','','TOTAL',rupiah(totals[0]),rupiah(totals[1]),rupiah(totals[2]),'']]
    )
