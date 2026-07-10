from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
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
from .models import OperationalExpense
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf, rupiah
from core.utils import parse_rupiah
from core.pagination import paginate_queryset
from cultivation.utils import get_selected_cycle, filter_selected_cycle


def _expense_queryset(request):
    date_from, date_to = get_date_range(request)
    items = filter_selected_cycle(request, OperationalExpense.objects.select_related('pond').order_by('-date'))
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
        OperationalExpense.objects.create(
            cycle=get_selected_cycle(request, required=True),
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
        obj.cycle = get_selected_cycle(request, required=True)
        obj.date = request.POST['date']
        obj.category = request.POST['category']
        obj.pond_id = request.POST.get('pond') or None
        obj.name = request.POST['name']
        obj.amount = parse_rupiah(request.POST.get('amount'))
        obj.payment_method = request.POST.get('payment_method', 'Cash')
        if request.FILES.get('receipt'):
            obj.receipt = request.FILES.get('receipt')
        obj.notes = request.POST.get('notes', '')
        obj.save()
        return redirect('finance:expenses')
    return render(request, 'finance/expense_form.html', {'ponds': ponds, 'categories': OperationalExpense.CATEGORIES, 'obj': obj, 'mode': 'edit'})

@login_required
@permission_required('finance.expenses')
@require_POST
def delete_expense(request, pk):
    get_object_or_404(OperationalExpense, pk=pk).delete()
    return redirect('finance:expenses')
