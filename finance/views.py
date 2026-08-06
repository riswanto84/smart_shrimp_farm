from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from accounts.rbac import permission_required
from django.db.models import Sum, Count, Min, Max, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import json
import mimetypes
from ponds.models import Pond
from operations.services.biomass import calculate_index_biomass_snapshot
from sales.models import Sale, Customer
from .models import OperationalExpense, ExpenseDocument, TradeAccount, TradePayment, TradeDocument, BalanceEntry, FixedAsset, OtherRevenue
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf, rupiah
from core.utils import parse_rupiah
from core.pagination import paginate_queryset
from cultivation.utils import get_selected_cycle, filter_selected_cycle
from cultivation.models import CultivationCycle
from finance.services.profit_loss import calculate_profit_loss


EXPENSE_DOCUMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx', '.xls', '.xlsx'}
EXPENSE_DOCUMENT_MAX_SIZE = 10 * 1024 * 1024


def _save_expense_documents(request, expense):
    description = request.POST.get('document_description', '').strip()
    saved_count = 0
    for uploaded_file in request.FILES.getlist('documents'):
        # Path.name membuang komponen folder dari nama file yang dikirim browser.
        safe_name = Path(uploaded_file.name).name
        extension = Path(safe_name).suffix.lower()
        if extension not in EXPENSE_DOCUMENT_EXTENSIONS:
            messages.error(request, f'File {safe_name} tidak didukung.')
            continue
        if uploaded_file.size > EXPENSE_DOCUMENT_MAX_SIZE:
            messages.error(request, f'File {safe_name} melebihi batas 10 MB.')
            continue
        ExpenseDocument.objects.create(
            expense=expense,
            file=uploaded_file,
            original_name=safe_name[:255],
            description=description[:180],
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        saved_count += 1
    if saved_count:
        messages.success(request, f'{saved_count} dokumen pengeluaran berhasil diunggah.')
    return saved_count


def _expense_queryset(request):
    date_from, date_to = get_date_range(request)
    items = filter_selected_cycle(request, OperationalExpense.objects.select_related('pond').prefetch_related('documents').order_by('-date'))
    items = filter_by_date_range(items, 'date', date_from, date_to)
    category = request.GET.get('category') or ''
    pond = request.GET.get('pond') or ''
    if category:
        items = items.filter(category=category)
    if pond:
        items = items.filter(pond_id=pond)
    q = (request.GET.get('q') or '').strip()
    if q:
        items = items.filter(
            Q(category__icontains=q) |
            Q(name__icontains=q) |
            Q(payment_method__icontains=q) |
            Q(notes__icontains=q) |
            Q(document_number__icontains=q) |
            Q(pond__name__icontains=q)
        ).distinct()
    return items, date_from, date_to


def _expense_rows(items):
    """Build raw expense rows for export.

    Keep ``amount`` as a Decimal so it is formatted exactly once by each
    exporter. Previously the value was converted to a Rupiah string here and
    then formatted again in the PDF exporter, causing every detail row to be
    rendered as Rp 0.
    """
    rows = []
    for i in items:
        rows.append([
            i.date.strftime('%d/%m/%Y'),
            i.category,
            i.name,
            i.amount or Decimal('0'),
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
        ['Tanggal', 'Kategori', 'Nama Pengeluaran', 'Jumlah', 'Metode Bayar', 'Catatan'],
        rows,
        [['', '', 'TOTAL', total, '', '']]
    )


@login_required
@permission_required('finance.expenses')
def export_expenses_pdf(request):
    items, date_from, date_to = _expense_queryset(request)
    rows = _expense_rows(items)
    total = items.aggregate(s=Sum('amount'))['s'] or 0
    pdf_rows = [[r[0], r[1], r[2], rupiah(r[3]), r[4], r[5]] for r in rows]
    return export_pdf(
        'laporan_pengeluaran_operasional',
        'Laporan Pengeluaran Operasional',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kategori', 'Nama Pengeluaran', 'Jumlah', 'Metode', 'Catatan'],
        pdf_rows,
        [['', '', 'TOTAL', rupiah(total), '', '']]
    )


@login_required
@permission_required('finance.expenses')
def add_expense(request):
    ponds = Pond.objects.all()
    if request.method == 'POST':
        expense = OperationalExpense.objects.create(
            cycle=get_selected_cycle(request, required=True),
            date=request.POST['date'],
            category=request.POST['category'],
            pond_id=request.POST.get('pond') or None,
            name=request.POST['name'],
            amount=parse_rupiah(request.POST.get('amount')),
            payment_method=request.POST.get('payment_method', 'Cash'),
            receipt=request.FILES.get('receipt'),
            notes=request.POST.get('notes', ''),
            is_capital_expenditure=request.POST.get('is_capital_expenditure') == '1',
            fixed_asset_id=request.POST.get('fixed_asset') or None,
        )
        _save_expense_documents(request, expense)
        return redirect('finance:expenses')
    return render(request, 'finance/expense_form.html', {'ponds': ponds, 'categories': OperationalExpense.CATEGORIES, 'fixed_assets': FixedAsset.objects.order_by('code')})


def _financial_report_scope(request, *, balance=False):
    """Resolve cycle-based or cross-cycle period reporting consistently."""
    today = timezone.localdate()
    mode = (request.GET.get('report_mode') or 'cycle').strip().lower()
    if mode not in ('cycle', 'period'):
        mode = 'cycle'
    cycles = CultivationCycle.objects.all().order_by('-start_date', '-id')
    cycle = get_selected_cycle(request) if mode == 'cycle' else None

    if balance:
        as_of = parse_date(request.GET.get('as_of') or request.GET.get('date_to') or '')
        if not as_of:
            if cycle and cycle.status == CultivationCycle.STATUS_COMPLETED and cycle.actual_end_date:
                as_of = cycle.actual_end_date
            else:
                as_of = today
        if as_of > today:
            as_of = today
        date_from = None
        if mode == 'period':
            date_from = parse_date(request.GET.get('date_from') or '') or date(as_of.year, 1, 1)
        return {
            'report_mode': mode, 'selected_cycle': cycle, 'cycles': cycles,
            'date_from': date_from, 'date_to': as_of, 'as_of': as_of,
        }

    if mode == 'period':
        date_from, date_to = _date_period(request)
    else:
        date_from = parse_date(request.GET.get('date_from') or '')
        date_to = parse_date(request.GET.get('date_to') or '') or today
    return {
        'report_mode': mode, 'selected_cycle': cycle, 'cycles': cycles,
        'date_from': date_from, 'date_to': date_to,
    }


def _scope_subtitle(scope, *, balance=False):
    if scope['report_mode'] == 'cycle' and scope.get('selected_cycle'):
        cycle = scope['selected_cycle']
        return f"Siklus: {cycle.name}"
    if balance:
        return f"Posisi per {scope['as_of'].strftime('%d/%m/%Y')}"
    return f"Periode: {format_date_range(scope.get('date_from'), scope.get('date_to'))}"


def _profit_loss_data(request):
    scope = _financial_report_scope(request)
    result = calculate_profit_loss(
        cycle=scope['selected_cycle'],
        date_from=scope['date_from'],
        date_to=scope['date_to'],
    )
    return scope, result


@login_required
@permission_required('finance.profit_loss')
def profit_loss(request):
    scope, result = _profit_loss_data(request)
    return render(request, 'finance/profit_loss.html', {**scope, **result})


@login_required
@permission_required('finance.profit_loss')
def export_profit_loss_excel(request):
    scope, result = _profit_loss_data(request)
    rows = [
        ['Pendapatan Penjualan dan Lainnya', rupiah(result['revenue'])],
        ['Pengeluaran Operasional', rupiah(result['expense_total'])],
        ['Laba/Rugi Bersih', rupiah(result['profit'])],
    ]
    return export_excel('laporan_laba_rugi', 'Laporan Laba Rugi', _scope_subtitle(scope), ['Uraian', 'Jumlah'], rows)


@login_required
@permission_required('finance.profit_loss')
def export_profit_loss_pdf(request):
    scope, result = _profit_loss_data(request)
    rows = [
        ['Pendapatan Penjualan dan Lainnya', rupiah(result['revenue'])],
        ['Pengeluaran Operasional', rupiah(result['expense_total'])],
        ['Laba/Rugi Bersih', rupiah(result['profit'])],
    ]
    return export_pdf('laporan_laba_rugi', 'Laporan Laba Rugi', _scope_subtitle(scope), ['Uraian', 'Jumlah'], rows)


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
        # Kirim object Python langsung ke json_script. Jangan json.dumps di sini,
        # karena json_script akan melakukan serialisasi sendiri. Serialisasi ganda
        # membuat JavaScript menerima string JSON, bukan object, sehingga dataset
        # Chart.js menjadi undefined/NaN dan grafik tidak tergambar.
        'series_json': series,
        'expense_chart_json': {
            'labels': [i['label'] for i in composition],
            'values': [_safe_float(i['amount']) for i in composition],
        },
        'payment_chart_json': {
            'labels': [i['label'] for i in payment_rows],
            'values': [_safe_float(i['amount']) for i in payment_rows],
        },
        'aging_chart_json': {
            'labels': [i['label'] for i in aging_rows],
            'values': [_safe_float(i['amount']) for i in aging_rows],
        },
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
        obj.is_capital_expenditure = request.POST.get('is_capital_expenditure') == '1'
        obj.fixed_asset_id = request.POST.get('fixed_asset') or None
        obj.save()
        _save_expense_documents(request, obj)
        return redirect('finance:expenses')
    return render(request, 'finance/expense_form.html', {'ponds': ponds, 'categories': OperationalExpense.CATEGORIES, 'fixed_assets': FixedAsset.objects.order_by('code'), 'obj': obj, 'mode': 'edit'})



@login_required
@permission_required('finance.expenses')
def preview_expense_document(request, pk):
    """Menampilkan dokumen pengeluaran secara inline dengan pemeriksaan hak akses."""
    document = get_object_or_404(ExpenseDocument.objects.select_related('expense'), pk=pk)
    if not document.file:
        raise Http404('Dokumen tidak tersedia.')
    try:
        file_handle = document.file.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('Berkas dokumen tidak ditemukan pada media penyimpanan.')
    filename = document.original_name or Path(document.file.name).name
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    response = FileResponse(file_handle, as_attachment=False, filename=filename, content_type=content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@permission_required('finance.expenses')
def preview_expense_receipt(request, pk):
    """Preview bukti lama (field receipt) tanpa membuka URL media secara langsung."""
    expense = get_object_or_404(OperationalExpense, pk=pk)
    if not expense.receipt:
        raise Http404('Bukti pengeluaran tidak tersedia.')
    try:
        file_handle = expense.receipt.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('Berkas bukti tidak ditemukan pada media penyimpanan.')
    filename = Path(expense.receipt.name).name
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    response = FileResponse(file_handle, as_attachment=False, filename=filename, content_type=content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    return response

@login_required
@permission_required('finance.expenses')
@require_POST
def upload_expense_documents(request, pk):
    expense = get_object_or_404(OperationalExpense, pk=pk)
    if not request.FILES.getlist('documents'):
        messages.warning(request, 'Pilih minimal satu dokumen untuk diunggah.')
    else:
        _save_expense_documents(request, expense)
    return redirect('finance:edit_expense', pk=expense.pk)


@login_required
@permission_required('finance.expenses')
@require_POST
def delete_expense_document(request, pk):
    document = get_object_or_404(ExpenseDocument, pk=pk)
    expense_id = document.expense_id
    if document.file:
        document.file.delete(save=False)
    document.delete()
    messages.success(request, 'Dokumen pengeluaran berhasil dihapus.')
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
from django.db.models import Q
from django.http import HttpResponse
from .models import OtherRevenue, BalanceEntry, FixedAsset, TradeAccount, TradePayment
from finance.services.depreciation import (
    calculate_asset_depreciation,
    calculate_depreciation_summary,
    fiscal_life_years,
    months_used,
)


def _as_date(request):
    return parse_date(request.GET.get('as_of') or '') or timezone.localdate()


def _date_period(request):
    """Return a safe reporting period.

    For the current year the default end date is today, not 31 December.
    This prevents future depreciation from being recognised in a report that
    is opened during the year. An explicitly supplied future end date is also
    capped at today for the current/future year.
    """
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year') or today.year)
    except (TypeError, ValueError):
        year = today.year

    default_from = timezone.datetime(year, 1, 1).date()
    default_to = today if year >= today.year else timezone.datetime(year, 12, 31).date()

    date_from = parse_date(request.GET.get('date_from') or '') or default_from
    date_to = parse_date(request.GET.get('date_to') or '') or default_to

    # Financial reports must not recognise future transactions/depreciation.
    if date_to > today:
        date_to = today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _fiscal_life(group):
    return fiscal_life_years(group)


def _months_used(asset, as_of):
    return months_used(asset, as_of)


def _asset_depreciation(asset, as_of):
    return calculate_asset_depreciation(asset, as_of)


def _calculate_profit_loss_period(date_from, date_to, cycle=None):
    """Backward-compatible wrapper around the central finance service."""
    return calculate_profit_loss(
        cycle=cycle,
        date_from=date_from,
        date_to=date_to,
    )


def _gross_turnover_data(request):
    scope = _financial_report_scope(request)
    sales = Sale.objects.exclude(status__in=['Gagal','Expired','Dibatalkan','Refund'])
    other = OtherRevenue.objects.all()
    if scope['selected_cycle'] is not None:
        sales = sales.filter(cycle=scope['selected_cycle'])
        other = other.filter(cycle=scope['selected_cycle'])
    if scope['date_from']:
        sales = sales.filter(date__date__gte=scope['date_from'])
        other = other.filter(date__gte=scope['date_from'])
    if scope['date_to']:
        sales = sales.filter(date__date__lte=scope['date_to'])
        other = other.filter(date__lte=scope['date_to'])
    rows = []
    for item in sales.select_related('customer').order_by('date'):
        rows.append({'date': item.date.date(), 'document': item.invoice_no, 'customer': item.customer.name if item.customer else '-', 'source': 'Penjualan Udang', 'amount': item.total_amount, 'kind': 'sale'})
    for item in other.order_by('date'):
        rows.append({'date': item.date, 'document': item.document_number or '-', 'customer': item.customer or '-', 'source': item.revenue_type, 'amount': item.gross_amount, 'kind': 'other'})
    rows.sort(key=lambda r: r['date'])
    total = sum((r['amount'] for r in rows), Decimal('0'))
    monthly = []
    for month in range(1,13):
        value = sum((r['amount'] for r in rows if scope['date_from'] and r['date'].year == scope['date_from'].year and r['date'].month == month), Decimal('0'))
        monthly.append({'month': month, 'label': timezone.datetime(2000,month,1).strftime('%B'), 'amount': value})
    return scope, rows, total, monthly


@login_required
@permission_required('finance.tax_reports')
def tax_dashboard(request):
    date_from, date_to = _date_period(request)
    sale_turnover = Sale.objects.filter(date__date__range=(date_from, date_to)).exclude(status__in=['Gagal','Expired','Dibatalkan','Refund']).aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
    other_turnover = OtherRevenue.objects.filter(date__range=(date_from, date_to)).aggregate(s=Sum('gross_amount'))['s'] or Decimal('0')
    turnover = sale_turnover + other_turnover
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
    scope,rows,total,monthly=_gross_turnover_data(request)
    return render(request,'finance/gross_turnover.html',{**scope,'rows':rows,'total':total,'monthly':monthly})


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
    scope,rows,total,_=_gross_turnover_data(request)
    data=[[r['date'].strftime('%d/%m/%Y'),r['document'],r['customer'],r['source'],rupiah(r['amount'])] for r in rows]
    return export_excel('peredaran_bruto','Laporan Peredaran Bruto',_scope_subtitle(scope),['Tanggal','Nomor Bukti','Pelanggan','Sumber Pendapatan','Peredaran Bruto'],data,[['','','','TOTAL',rupiah(total)]])


@login_required
@permission_required('finance.tax_reports')
def export_gross_turnover_pdf(request):
    scope,rows,total,_=_gross_turnover_data(request)
    data=[[r['date'].strftime('%d/%m/%Y'),r['document'],r['customer'],r['source'],rupiah(r['amount'])] for r in rows]
    return export_pdf('peredaran_bruto','Laporan Peredaran Bruto',_scope_subtitle(scope),['Tanggal','Nomor Bukti','Pelanggan','Sumber Pendapatan','Peredaran Bruto'],data,[['','','','TOTAL',rupiah(total)]])


def _profit_loss_tax_data(request):
    selected_cycle = get_selected_cycle(request)
    has_explicit_period = any(
        request.GET.get(key) for key in ('date_from', 'date_to', 'year')
    )
    if has_explicit_period:
        date_from, date_to = _date_period(request)
    else:
        # Tanpa filter eksplisit, samakan dengan Dashboard dan Neraca: seluruh
        # transaksi pada siklus terpilih sampai hari ini.
        date_from, date_to = None, timezone.localdate()

    result = _calculate_profit_loss_period(
        date_from, date_to, cycle=selected_cycle
    )
    grouped = list(result['grouped'])
    # Kategori Penyusutan sudah berada di OperationalExpense dan sudah masuk
    # grouped/expense_total. Jangan menambahkan baris otomatis kedua.
    non_deductible = (
        result['expenses'].filter(is_fiscal_deductible=False)
        .aggregate(s=Sum('amount'))['s']
        or Decimal('0')
    )
    return (
        date_from,
        date_to,
        result['revenue'],
        grouped,
        result['expense_total'],
        result['profit'],
        non_deductible,
    )


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



OPENING_BALANCE_ACCOUNTS = (
    # field, account type, group, account name, allow negative
    ('cash', 'asset', 'Kas dan Bank', 'Kas Tunai', False),
    ('bank_bca', 'asset', 'Kas dan Bank', 'Bank BCA', False),
    ('bank_mandiri', 'asset', 'Kas dan Bank', 'Bank Mandiri', False),
    ('bank_bri', 'asset', 'Kas dan Bank', 'Bank BRI', False),
    ('bank_other', 'asset', 'Kas dan Bank', 'Bank Lainnya', False),
    ('inventory', 'asset', 'Persediaan', 'Persediaan Awal', False),
    ('advances', 'asset', 'Uang Muka', 'Uang Muka Awal', False),
    ('other_current_assets', 'asset', 'Aset Lancar Lainnya', 'Aset Lancar Lainnya', False),
    ('tax_payable', 'liability', 'Utang Pajak', 'Utang Pajak Awal', False),
    ('owner_payable', 'liability', 'Utang Pemilik', 'Utang Pemilik Awal', False),
    ('other_liabilities', 'liability', 'Utang Lainnya', 'Utang Lainnya', False),
    ('owner_capital', 'equity', 'Modal Pemilik', 'Modal Pemilik', True),
    ('additional_capital', 'equity', 'Tambahan Modal', 'Tambahan Modal', True),
    ('drawings', 'equity', 'Prive', 'Prive', True),
    ('retained_earnings', 'equity', 'Laba Ditahan', 'Laba Ditahan', True),
)


def _opening_balance_values(as_of):
    values = {}
    for field, account_type, group, account_name, allow_negative in OPENING_BALANCE_ACCOUNTS:
        entry = (BalanceEntry.objects
                 .filter(as_of_date__lte=as_of, account_type=account_type,
                         group=group, account_name=account_name)
                 .order_by('-as_of_date', '-id').first())
        values[field] = entry.amount if entry else Decimal('0')
    return values


def _automatic_opening_components(as_of):
    """Komponen neraca yang berasal dari modul transaksi, bukan input saldo awal."""
    def outstanding_as_of(account):
        paid = account.payments.filter(payment_date__lte=as_of).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        return max((account.original_amount or Decimal('0')) - paid, Decimal('0'))

    receivables = sum((outstanding_as_of(x) for x in TradeAccount.objects.filter(
        account_type=TradeAccount.RECEIVABLE, transaction_date__lte=as_of
    )), Decimal('0'))
    payables = sum((outstanding_as_of(x) for x in TradeAccount.objects.filter(
        account_type=TradeAccount.PAYABLE, transaction_date__lte=as_of
    )), Decimal('0'))

    fixed_cost = Decimal('0')
    accumulated = Decimal('0')
    for asset in FixedAsset.objects.filter(use_date__lte=as_of).exclude(status='disposed'):
        fixed_cost += asset.total_cost
        accumulated += _asset_depreciation(asset, as_of)['accumulated']

    start = timezone.datetime(as_of.year, 1, 1).date()
    current_profit = _calculate_profit_loss_period(start, as_of)['profit']
    return {
        'receivables': receivables,
        'payables': payables,
        'fixed_cost': fixed_cost,
        'accumulated': accumulated,
        'net_fixed_assets': fixed_cost - accumulated,
        'current_profit': current_profit,
    }


@login_required
@permission_required('finance.tax_reports')
def opening_balance(request):
    """Wizard rekonsiliasi saldo awal berbasis akun neraca yang sebenarnya.

    Piutang, utang usaha, aset tetap, penyusutan, serta laba tahun berjalan
    tetap bersumber dari modul transaksi agar tidak terjadi pencatatan ganda.
    """
    raw_as_of = request.POST.get('as_of_date') or request.GET.get('as_of')
    if isinstance(raw_as_of, timezone.datetime):
        as_of = raw_as_of.date()
    elif hasattr(raw_as_of, 'year') and hasattr(raw_as_of, 'month') and hasattr(raw_as_of, 'day'):
        # Sudah berupa date; jangan dikirim lagi ke parse_date/fromisoformat.
        as_of = raw_as_of
    else:
        as_of = parse_date(str(raw_as_of or '')) or timezone.localdate()
    automatic = _automatic_opening_components(as_of)

    if request.method == 'POST':
        parsed = {}
        errors = []
        for field, account_type, group, account_name, allow_negative in OPENING_BALANCE_ACCOUNTS:
            value = parse_rupiah(request.POST.get(field, '0'))
            if not allow_negative and value < 0:
                errors.append(f'{account_name} tidak boleh bernilai negatif.')
            parsed[field] = value

        # Prive merupakan pengurang ekuitas. Pengguna cukup memasukkan angka positif.
        if parsed.get('drawings', Decimal('0')) > 0:
            parsed['drawings'] = -parsed['drawings']

        if request.POST.get('action') == 'auto_reconcile' and not errors:
            manual_assets = sum((parsed[field] for field, typ, *_ in OPENING_BALANCE_ACCOUNTS if typ == 'asset'), Decimal('0'))
            manual_liabilities = sum((parsed[field] for field, typ, *_ in OPENING_BALANCE_ACCOUNTS if typ == 'liability'), Decimal('0'))
            other_equity = sum((parsed[field] for field, typ, *_ in OPENING_BALANCE_ACCOUNTS if typ == 'equity' and field != 'owner_capital'), Decimal('0'))
            total_assets = manual_assets + automatic['receivables'] + automatic['net_fixed_assets']
            total_liabilities = manual_liabilities + automatic['payables']
            parsed['owner_capital'] = total_assets - total_liabilities - automatic['current_profit'] - other_equity

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            for field, account_type, group, account_name, allow_negative in OPENING_BALANCE_ACCOUNTS:
                BalanceEntry.objects.update_or_create(
                    as_of_date=as_of,
                    account_type=account_type,
                    group=group,
                    account_name=account_name,
                    defaults={
                        'amount': parsed[field],
                        'notes': 'Saldo awal melalui wizard rekonsiliasi',
                    },
                )
            if request.POST.get('action') == 'auto_reconcile':
                messages.success(request, 'Saldo awal berhasil direkonsiliasi. Modal Pemilik dihitung otomatis agar persamaan neraca seimbang tanpa akun sementara.')
            else:
                messages.success(request, 'Saldo awal berhasil disimpan dan langsung digunakan pada laporan neraca.')
            return redirect(f"{request.path}?as_of={as_of.isoformat()}")

    values = _opening_balance_values(as_of)
    # Prive ditampilkan positif agar lebih mudah diinput pengguna.
    values['drawings_display'] = abs(values.get('drawings', Decimal('0')))

    cash_bank_total = sum((values[k] for k in ('cash','bank_bca','bank_mandiri','bank_bri','bank_other')), Decimal('0'))
    manual_asset_total = sum((values[field] for field, typ, *_ in OPENING_BALANCE_ACCOUNTS if typ == 'asset'), Decimal('0'))
    manual_liability_total = sum((values[field] for field, typ, *_ in OPENING_BALANCE_ACCOUNTS if typ == 'liability'), Decimal('0'))
    equity_opening_total = sum((values[field] for field, typ, *_ in OPENING_BALANCE_ACCOUNTS if typ == 'equity'), Decimal('0'))

    total_assets_preview = manual_asset_total + automatic['receivables'] + automatic['net_fixed_assets']
    total_liabilities_preview = manual_liability_total + automatic['payables']
    total_equity_preview = equity_opening_total + automatic['current_profit']
    reconciliation_difference = total_assets_preview - total_liabilities_preview - total_equity_preview

    context = {
        'as_of': as_of,
        'values': values,
        'cash_bank_total': cash_bank_total,
        'manual_asset_total': manual_asset_total,
        'manual_liability_total': manual_liability_total,
        'equity_opening_total': equity_opening_total,
        'auto_receivables': automatic['receivables'],
        'auto_payables': automatic['payables'],
        'auto_fixed_assets': automatic['fixed_cost'],
        'auto_accumulated_depreciation': automatic['accumulated'],
        'auto_net_fixed_assets': automatic['net_fixed_assets'],
        'auto_current_profit': automatic['current_profit'],
        'total_assets_preview': total_assets_preview,
        'total_liabilities_preview': total_liabilities_preview,
        'total_equity_preview': total_equity_preview,
        'reconciliation_difference': reconciliation_difference,
        'is_reconciled_preview': abs(reconciliation_difference) < Decimal('0.01'),
    }
    return render(request, 'finance/opening_balance.html', context)


def _balance_sheet_data(request):
    """Susun neraca dengan sumber data operasional yang transparan.

    Pos manual tetap dipakai sebagai saldo posisi. Piutang, utang, aset tetap,
    penyusutan, dan laba berjalan dihitung otomatis. Apabila data historis
    belum lengkap, selisih ditempatkan pada akun rekonsiliasi sementara agar
    laporan tetap seimbang tanpa menyembunyikan bahwa saldo awal/modal perlu
    dilengkapi.
    """
    from .receivable_sync import sync_all_sales

    scope = _financial_report_scope(request, balance=True)
    as_of = scope['as_of']
    selected_cycle = scope['selected_cycle']
    sync_all_sales()

    latest = {}
    for e in BalanceEntry.objects.filter(as_of_date__lte=as_of).order_by('account_name', '-as_of_date', '-id'):
        latest.setdefault((e.account_type, e.account_name), e)
    entries = list(latest.values())

    assets = [e for e in entries if e.account_type == 'asset' and e.group not in ('Aset Tetap', 'Piutang Usaha')]
    liabilities = [e for e in entries if e.account_type == 'liability' and e.group != 'Utang Usaha']
    equities = [e for e in entries if e.account_type == 'equity']

    def outstanding_as_of(account):
        paid = account.payments.filter(payment_date__lte=as_of).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        return max((account.original_amount or Decimal('0')) - paid, Decimal('0'))

    receivable_total = sum((outstanding_as_of(x) for x in TradeAccount.objects.filter(account_type=TradeAccount.RECEIVABLE, transaction_date__lte=as_of)), Decimal('0'))
    payable_total = sum((outstanding_as_of(x) for x in TradeAccount.objects.filter(account_type=TradeAccount.PAYABLE, transaction_date__lte=as_of)), Decimal('0'))

    fixed_assets = []
    for a in FixedAsset.objects.filter(use_date__lte=as_of).exclude(status='disposed'):
        dep = _asset_depreciation(a, as_of)
        fixed_assets.append({'asset': a, **dep})
    fixed_cost = sum((x['asset'].total_cost for x in fixed_assets), Decimal('0'))
    accumulated = sum((x['accumulated'] for x in fixed_assets), Decimal('0'))

    # Aset biologis udang yang masih berada di kolam. Nilai dihitung dari
    # populasi sampling terbaru yang diproyeksikan dengan ADG sampai tanggal
    # neraca, lalu dikurangi populasi panen parsial dan mortalitas setelah
    # sampling. Harga dipilih berdasarkan size terdekat dari penjualan aktual.
    from operations.models import SamplingRecord, Harvest, SiphonRecord
    from ponds.models import Pond
    from sales.models import SaleItem
    import re

    def decimal_value(value, default='0'):
        try:
            return Decimal(str(value if value is not None else default))
        except Exception:
            return Decimal(default)

    def size_number(value):
        numbers = re.findall(r'\d+(?:[.,]\d+)?', str(value or '').replace(',', '.'))
        if not numbers:
            return None
        values = [Decimal(x) for x in numbers]
        return sum(values, Decimal('0')) / Decimal(len(values))

    # Peta harga rata-rata tertimbang per size. Ini membuat nilai tiap kolam
    # mengikuti ukuran udang, bukan memakai satu harga rata-rata untuk semua.
    sale_price_buckets = {}
    sold_items_qs = SaleItem.objects.filter(
        sale__date__date__lte=as_of,
        weight_kg__gt=0,
        price_per_kg__gt=0,
    ).exclude(sale__status__in=['Gagal', 'Expired', 'Dibatalkan', 'Refund'])
    if selected_cycle is not None:
        sold_items_qs = sold_items_qs.filter(sale__cycle=selected_cycle)
    sold_items = sold_items_qs.values('size_text', 'weight_kg', 'price_per_kg')
    sold_amount = Decimal('0')
    sold_weight = Decimal('0')
    for row in sold_items:
        weight = decimal_value(row['weight_kg'])
        price_row = decimal_value(row['price_per_kg'])
        sold_weight += weight
        sold_amount += weight * price_row
        parsed_size = size_number(row['size_text'])
        if parsed_size is None:
            continue
        key = int(parsed_size.quantize(Decimal('1')))
        bucket = sale_price_buckets.setdefault(key, {'weight': Decimal('0'), 'amount': Decimal('0')})
        bucket['weight'] += weight
        bucket['amount'] += weight * price_row
    average_sale_price = (sold_amount / sold_weight) if sold_weight else Decimal('0')

    def market_price_for_size(current_size, cycle):
        # Kebijakan penilaian biologis: seluruh biomassa aktif memakai harga
        # jual rata-rata tertimbang aktual pada siklus yang dipilih. Size tetap
        # ditampilkan sebagai informasi biologis, tetapi tidak lagi membuat
        # nilai antar-kolam memakai sumber harga berbeda.
        if average_sale_price > 0:
            return (
                average_sale_price,
                'Harga jual rata-rata tertimbang siklus',
                {'class': 'green', 'label': 'Rata-rata aktual'},
            )
        if cycle and decimal_value(getattr(cycle, 'estimated_price_per_kg', 0)) > 0:
            return (
                decimal_value(cycle.estimated_price_per_kg),
                'Estimasi harga siklus',
                {'class': 'amber', 'label': 'Harga estimasi'},
            )
        return Decimal('0'), 'Belum tersedia', {'class': 'red', 'label': 'Harga belum ada'}

    def is_total_harvest(value):
        text = str(value or '').strip().lower().replace('_', ' ').replace('-', ' ')
        return text in {'total', 'final', 'panen total', 'panen final', 'selesai'}

    def metric_health(kind, value, *, target=None):
        value = decimal_value(value)
        if kind == 'sampling':
            days = int(value)
            if days <= 14:
                return {'class': 'green', 'label': 'Terkini'}
            if days <= 30:
                return {'class': 'amber', 'label': 'Perlu sampling'}
            return {'class': 'red', 'label': 'Kedaluwarsa'}
        if kind == 'adg':
            target = decimal_value(target or '0.25')
            if Decimal('0.03') <= value <= Decimal('0.60') and value >= target * Decimal('0.85'):
                return {'class': 'green', 'label': 'Normal'}
            if Decimal('0') < value <= Decimal('0.60'):
                return {'class': 'amber', 'label': 'Di bawah target'}
            return {'class': 'red', 'label': 'Tidak wajar'}
        if kind == 'sr':
            if Decimal('75') <= value <= Decimal('100'):
                return {'class': 'green', 'label': 'Sehat'}
            if Decimal('60') <= value <= Decimal('105'):
                return {'class': 'amber', 'label': 'Waspada'}
            return {'class': 'red', 'label': 'Perlu validasi'}
        if kind == 'fcr':
            if Decimal('0') < value <= Decimal('1.40'):
                return {'class': 'green', 'label': 'Efisien'}
            if Decimal('1.40') < value <= Decimal('1.70'):
                return {'class': 'amber', 'label': 'Waspada'}
            return {'class': 'red', 'label': 'Tidak efisien/data kosong'}
        return {'class': 'gray', 'label': 'Belum dinilai'}

    # Dashboard dan Neraca memakai snapshot biomassa INDEX yang sama.
    index_snapshot = calculate_index_biomass_snapshot(as_of=as_of)
    if selected_cycle is not None:
        index_snapshot['rows'] = [row for row in index_snapshot['rows'] if row.cycle and row.cycle.pk == selected_cycle.pk]
        index_snapshot['excluded'] = [row for row in index_snapshot['excluded'] if row.cycle and row.cycle.pk == selected_cycle.pk]
        index_snapshot['total_kg'] = sum((row.biomass_index_kg for row in index_snapshot['rows']), Decimal('0'))
    pond_assets = []
    excluded_pond_assets = [
        {'pond': row.pond, 'reason': row.exclusion_reason}
        for row in index_snapshot['excluded']
    ]
    biological_assets_total = Decimal('0')

    for result in index_snapshot['rows']:
        pond = result.pond
        latest_sampling = result.sampling
        cycle = result.cycle
        raw_biomass = result.sampling_biomass_index_kg
        sampling_abw = result.sampling_abw_g
        sampling_age = result.sampling_age_days
        target_adg = decimal_value(getattr(cycle, 'target_adg', Decimal('0.25')) if cycle else Decimal('0.25'))
        adg = result.adg_g_per_day
        projected_abw = result.projected_abw_g
        current_size = result.size
        partial_harvest_kg = result.partial_harvest_kg
        partial_harvest_population = result.harvested_population
        mortality_population = result.mortality_population
        remaining_population = result.remaining_population_index
        biomass = result.biomass_index_kg
        growth_kg = result.growth_index_kg
        mortality_kg = result.mortality_index_kg
        net_change_kg = biomass - raw_biomass
        current_sr = (
            Decimal(remaining_population) / Decimal(latest_sampling.stocking_count) * Decimal('100')
            if latest_sampling.stocking_count else decimal_value(latest_sampling.sr_index_percent or latest_sampling.estimated_sr)
        )
        fcr = decimal_value(latest_sampling.fcr)

        price, price_source, price_health = market_price_for_size(current_size, cycle)
        value = (biomass * price).quantize(Decimal('0.01'))
        biological_assets_total += value

        sampling_health = metric_health('sampling', sampling_age)
        adg_health = metric_health('adg', adg, target=target_adg)
        sr_health = metric_health('sr', current_sr)
        fcr_health = metric_health('fcr', fcr)
        if biomass <= 0:
            biomass_health = {'class': 'red', 'label': 'Biomassa nol'}
        elif raw_biomass > 0 and net_change_kg < -(raw_biomass * Decimal('0.25')):
            biomass_health = {'class': 'red', 'label': 'Turun tajam'}
        elif net_change_kg < 0:
            biomass_health = {'class': 'amber', 'label': 'Menurun'}
        else:
            biomass_health = {'class': 'green', 'label': 'Bertumbuh'}

        healths = [sampling_health, adg_health, sr_health, fcr_health, price_health, biomass_health]
        indicator = 'red' if any(x['class'] == 'red' for x in healths) else ('amber' if any(x['class'] == 'amber' for x in healths) else 'green')
        indicator_label = 'Kritis · perlu tindakan' if indicator == 'red' else ('Waspada · perlu dipantau' if indicator == 'amber' else 'Sehat · terkendali')

        pond_assets.append({
            'pond': pond, 'sampling': latest_sampling,
            'cycle_name': cycle.name if cycle else '-', 'doc': latest_sampling.doc or 0,
            'sampling_abw': sampling_abw, 'projected_abw': projected_abw,
            'current_size': current_size, 'adg': adg, 'target_adg': target_adg,
            'sr': current_sr, 'fcr': fcr, 'raw_biomass_kg': raw_biomass,
            'growth_kg': growth_kg, 'partial_harvest_kg': partial_harvest_kg,
            'partial_harvest_population': partial_harvest_population,
            'mortality_population': mortality_population, 'mortality_kg': mortality_kg,
            'remaining_population': remaining_population, 'biomass_kg': biomass,
            'net_change_kg': net_change_kg, 'price_per_kg': price,
            'price_source': price_source, 'asset_value': value,
            'sampling_age': sampling_age, 'indicator': indicator,
            'indicator_label': indicator_label, 'is_active_pond': True,
            'sampling_health': sampling_health, 'biomass_health': biomass_health,
            'adg_health': adg_health, 'sr_health': sr_health,
            'fcr_health': fcr_health, 'price_health': price_health,
            'biomass_method': 'INDEX',
        })

    # Gunakan konteks yang sama persis dengan Dashboard: seluruh transaksi yang
    # terhubung ke siklus terpilih sampai tanggal posisi neraca. Jangan memakai
    # tanggal mulai siklus sebagai filter tambahan karena transaksi yang sudah
    # ditautkan ke siklus dapat memiliki tanggal administrasi sebelum start_date.
    # Filter ganda tersebut sebelumnya membuat laba operasional Neraca berbeda.
    if selected_cycle is not None:
        profit_loss = _calculate_profit_loss_period(None, as_of, cycle=selected_cycle)
    else:
        start = scope.get('date_from') or timezone.datetime(as_of.year, 1, 1).date()
        profit_loss = _calculate_profit_loss_period(start, as_of, cycle=None)
    sales_revenue = profit_loss['sales_revenue']
    other_revenue = profit_loss['other_revenue']
    operating_cost = profit_loss['operating_cost']
    current_year_depreciation = profit_loss['depreciation_total']
    operating_profit = profit_loss['profit']

    # Rekonsiliasi aset biologis menggunakan baseline/snapshot yang jelas.
    # Tidak lagi memakai seluruh nilai biomassa sebagai akun penyeimbang
    # ``saldo awal/modal belum direkonsiliasi``. Baseline pertama merupakan
    # cadangan pengakuan awal aset biologis; perubahan setelah baseline
    # diakui sebagai kenaikan/penurunan nilai wajar pada laba/rugi berjalan.
    from .models import BiologicalAssetValuation
    valuation_snapshots = BiologicalAssetValuation.objects.filter(valuation_date__lte=as_of).order_by('valuation_date', 'id')
    first_snapshot = valuation_snapshots.first()
    previous_snapshot = valuation_snapshots.filter(valuation_date__lt=as_of).order_by('-valuation_date', '-id').first()

    if first_snapshot:
        biological_opening_reserve = decimal_value(first_snapshot.closing_value)
        biological_baseline_date = first_snapshot.valuation_date
        biological_fair_value_change_cumulative = biological_assets_total - biological_opening_reserve
        biological_fair_value_change_period = biological_assets_total - decimal_value(
            previous_snapshot.closing_value if previous_snapshot else first_snapshot.closing_value
        )
        biological_valuation_is_provisional = False
    else:
        # Fallback aman untuk instalasi lama: nilai saat ini diperlakukan sebagai
        # pengakuan awal, bukan laba periode berjalan. Jalankan perintah
        # ``initialize_biological_valuation`` untuk mengunci baseline tersebut.
        biological_opening_reserve = biological_assets_total
        biological_baseline_date = as_of
        biological_fair_value_change_cumulative = Decimal('0')
        biological_fair_value_change_period = Decimal('0')
        biological_valuation_is_provisional = biological_assets_total != 0

    current_profit = operating_profit + biological_fair_value_change_cumulative

    manual_asset_total = sum((e.amount for e in assets), Decimal('0'))
    total_assets_before = manual_asset_total + receivable_total + biological_assets_total + fixed_cost - accumulated
    total_liabilities = sum((e.amount for e in liabilities), Decimal('0')) + payable_total
    total_equity = sum((e.amount for e in equities), Decimal('0'))
    total_equity_before = total_equity + current_profit + biological_opening_reserve
    total_assets = total_assets_before
    difference = total_assets - total_liabilities - total_equity_before
    preliminary_difference = difference
    reconciliation_equity = Decimal('0')
    total_equity_with_profit = total_equity_before

    capital_expenses = OperationalExpense.objects.filter(date__lte=as_of, is_capital_expenditure=True).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    unlinked_capital_expenses = OperationalExpense.objects.filter(date__lte=as_of, is_capital_expenditure=True, fixed_asset__isnull=True).count()
    warnings = []
    if biological_valuation_is_provisional:
        warnings.append('Baseline aset biologis masih bersifat sementara. Jalankan python manage.py initialize_biological_valuation untuk mengunci nilai pengakuan awal.')
    if abs(difference) > Decimal('0.01'):
        warnings.append('Neraca masih memiliki selisih yang tidak dapat dijelaskan oleh aset biologis. Periksa saldo Kas/Bank, Modal Pemilik, Utang, dan saldo pembukaan.')
    if unlinked_capital_expenses:
        warnings.append(f'{unlinked_capital_expenses} pengeluaran kapital belum ditautkan ke Daftar Aset.')

    # Ringkasan analitis untuk dashboard neraca.
    cash_bank_total = sum((e.amount for e in assets if e.group == 'Kas dan Bank'), Decimal('0'))
    other_current_assets = sum((e.amount for e in assets if e.group != 'Kas dan Bank'), Decimal('0'))
    accounting_current_assets = cash_bank_total + other_current_assets + receivable_total
    operational_current_assets = accounting_current_assets + biological_assets_total
    current_assets = operational_current_assets
    net_fixed_assets = fixed_cost - accumulated

    def safe_ratio(numerator, denominator):
        return (numerator / denominator) if denominator else None

    current_ratio = safe_ratio(accounting_current_assets, total_liabilities)
    cash_ratio = safe_ratio(cash_bank_total, total_liabilities)
    operational_current_ratio = safe_ratio(operational_current_assets, total_liabilities)
    biomass_coverage = safe_ratio(biological_assets_total, total_liabilities)
    operational_working_capital = operational_current_assets - total_liabilities
    debt_to_equity = safe_ratio(total_liabilities, total_equity_with_profit) if total_equity_with_profit > 0 else None
    debt_ratio = safe_ratio(total_liabilities, total_assets)

    def ratio_health(value, green_min=None, amber_min=None, green_max=None, amber_max=None):
        if value is None:
            return {'class': 'gray', 'label': 'Belum dapat dinilai'}
        if green_min is not None:
            if value >= Decimal(str(green_min)):
                return {'class': 'green', 'label': 'Sehat'}
            if value >= Decimal(str(amber_min)):
                return {'class': 'amber', 'label': 'Waspada'}
            return {'class': 'red', 'label': 'Kritis'}
        if value <= Decimal(str(green_max)):
            return {'class': 'green', 'label': 'Sehat'}
        if value <= Decimal(str(amber_max)):
            return {'class': 'amber', 'label': 'Waspada'}
        return {'class': 'red', 'label': 'Kritis'}

    current_ratio_health = ratio_health(current_ratio, green_min=1.5, amber_min=1.0)
    cash_ratio_health = ratio_health(cash_ratio, green_min=1.0, amber_min=0.5)
    debt_to_equity_health = ratio_health(debt_to_equity, green_max=1.0, amber_max=2.0)
    debt_ratio_health = ratio_health(debt_ratio, green_max=0.5, amber_max=0.7)
    operational_current_health = ratio_health(operational_current_ratio, green_min=1.5, amber_min=1.0)
    biomass_coverage_health = ratio_health(biomass_coverage, green_min=1.0, amber_min=0.5)
    # Nilai biomassa aktif tidak boleh dinilai dari nominal rupiah absolut.
    # Kesehatan finansialnya mengikuti kemampuan nilai biomassa menutup kewajiban:
    # >= 2,00x sehat; 1,00-<2,00x waspada; < 1,00x kritis.
    # Kualitas/kelengkapan data kolam ditampilkan terpisah agar tidak mengubah
    # status finansial hanya karena salah satu parameter operasional perlu validasi.
    biomass_value_health = ratio_health(
        biomass_coverage, green_min=2.0, amber_min=1.0
    )
    biomass_data_health = (
        {'class': 'gray', 'label': 'Belum ada data'} if not pond_assets
        else {'class': 'red', 'label': 'Perlu validasi'} if any(x['indicator'] == 'red' for x in pond_assets)
        else {'class': 'amber', 'label': 'Perlu dipantau'} if any(x['indicator'] == 'amber' for x in pond_assets)
        else {'class': 'green', 'label': 'Data memadai'}
    )
    working_capital_health = (
        {'class': 'green', 'label': 'Sehat'} if operational_working_capital > 0
        else {'class': 'amber', 'label': 'Waspada'} if operational_working_capital == 0
        else {'class': 'red', 'label': 'Kritis'}
    )

    def percentage(part, whole):
        return (part / whole * Decimal('100')) if whole else Decimal('0')

    asset_composition = [
        {'label': 'Kas & Bank', 'amount': cash_bank_total, 'percent': percentage(cash_bank_total, total_assets)},
        {'label': 'Piutang Usaha', 'amount': receivable_total, 'percent': percentage(receivable_total, total_assets)},
        {'label': 'Biomassa di Kolam', 'amount': biological_assets_total, 'percent': percentage(biological_assets_total, total_assets)},
        {'label': 'Aset Lancar Lain', 'amount': other_current_assets, 'percent': percentage(other_current_assets, total_assets)},
        {'label': 'Aset Tetap Bersih', 'amount': net_fixed_assets, 'percent': percentage(net_fixed_assets, total_assets)},
    ]

    from finance.services.final_cycle_profit import calculate_final_cycle_profit
    final_cycle_profit = calculate_final_cycle_profit(
        cycle=selected_cycle,
        as_of=as_of,
        simulated_price=request.GET.get('simulation_price'),
    )

    validation_checks = [
        {'label': 'Persamaan neraca seimbang', 'ok': difference == 0},
        {'label': 'Baseline aset biologis telah ditetapkan', 'ok': not biological_valuation_is_provisional},
        {'label': 'Tidak ada pengeluaran kapital tanpa aset', 'ok': unlinked_capital_expenses == 0},
        {'label': 'Piutang dan nota penjualan tersinkron', 'ok': True},
        {'label': 'Seluruh kolam aktif memiliki data biomassa dan harga', 'ok': all(x['indicator'] != 'red' for x in pond_assets if x['is_active_pond'])},
    ]

    return {
        **scope,
        'as_of': as_of, 'assets': assets, 'liabilities': liabilities, 'equities': equities,
        'fixed_assets': fixed_assets, 'receivable_total': receivable_total, 'payable_total': payable_total,
        'fixed_cost': fixed_cost, 'accumulated': accumulated, 'net_fixed_assets': net_fixed_assets,
        'cash_bank_total': cash_bank_total, 'other_current_assets': other_current_assets,
        'biological_assets_total': biological_assets_total, 'pond_assets': pond_assets,
        'excluded_pond_assets': excluded_pond_assets,
        'average_sale_price': average_sale_price,
        'biological_price_source': ('Harga jual rata-rata tertimbang siklus' if average_sale_price > 0 else 'Harga estimasi siklus'),
        'final_cycle_profit': final_cycle_profit,
        'accounting_current_assets': accounting_current_assets,
        'operational_current_assets': operational_current_assets,
        'current_assets': current_assets, 'total_assets': total_assets,
        'total_liabilities': total_liabilities, 'total_equity': total_equity,
        'operating_profit': operating_profit, 'current_profit': current_profit, 'total_equity_before': total_equity_before,
        'biological_opening_reserve': biological_opening_reserve,
        'biological_baseline_date': biological_baseline_date,
        'biological_fair_value_change_cumulative': biological_fair_value_change_cumulative,
        'biological_fair_value_change_period': biological_fair_value_change_period,
        'biological_valuation_is_provisional': biological_valuation_is_provisional,
        'reconciliation_equity': reconciliation_equity,
        'total_equity_with_profit': total_equity_with_profit,
        'preliminary_difference': preliminary_difference, 'difference': difference,
        'sales_revenue': sales_revenue, 'other_revenue': other_revenue,
        'operating_cost': operating_cost, 'current_year_depreciation': current_year_depreciation,
        'capital_expenses': capital_expenses, 'warnings': warnings,
        'current_ratio': current_ratio, 'cash_ratio': cash_ratio,
        'debt_to_equity': debt_to_equity, 'debt_ratio': debt_ratio,
        'operational_current_ratio': operational_current_ratio,
        'biomass_coverage': biomass_coverage,
        'operational_working_capital': operational_working_capital,
        'current_ratio_health': current_ratio_health,
        'cash_ratio_health': cash_ratio_health,
        'debt_to_equity_health': debt_to_equity_health,
        'debt_ratio_health': debt_ratio_health,
        'operational_current_health': operational_current_health,
        'biomass_coverage_health': biomass_coverage_health,
        'biomass_value_health': biomass_value_health,
        'biomass_data_health': biomass_data_health,
        'working_capital_health': working_capital_health,
        'asset_composition': asset_composition, 'validation_checks': validation_checks,
        'is_balanced': difference == 0,
        'is_reconciled': abs(difference) <= Decimal('0.01') and not biological_valuation_is_provisional,
        'balance_status': (
            'balanced' if abs(difference) <= Decimal('0.01') and not biological_valuation_is_provisional
            else 'balanced_with_note' if abs(difference) <= Decimal('0.01')
            else 'unbalanced'
        ),
    }


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
    rows.append(['ASET - Biomassa Udang di Kolam', rupiah(d['biological_assets_total'])])
    for item in d['pond_assets']:
        if item['asset_value'] > 0:
            rows.append([f"  {item['pond'].name} - {item['biomass_kg']:,.2f} kg".replace(',', '.'), rupiah(item['asset_value'])])
    rows += [['Aset Tetap - Harga Perolehan',rupiah(d['fixed_cost'])],['Akumulasi Penyusutan',f"({rupiah(d['accumulated'])})"],['TOTAL ASET',rupiah(d['total_assets'])]]
    for e in d['liabilities']: rows.append([f"KEWAJIBAN - {e.account_name}",rupiah(e.amount)])
    rows.append(['KEWAJIBAN - Utang Usaha',rupiah(d['payable_total'])])
    rows.append(['TOTAL KEWAJIBAN',rupiah(d['total_liabilities'])])
    for e in d['equities']: rows.append([f"EKUITAS - {e.account_name}",rupiah(e.amount)])
    rows += [['Laba/Rugi Operasional Tahun Berjalan',rupiah(d['operating_profit'])],['Cadangan Pengakuan Awal Aset Biologis',rupiah(d['biological_opening_reserve'])],['Perubahan Nilai Wajar Aset Biologis',rupiah(d['biological_fair_value_change_cumulative'])],['Laba/Rugi Tahun Berjalan Setelah Penilaian Biologis',rupiah(d['current_profit'])],['TOTAL EKUITAS',rupiah(d['total_equity_with_profit'])],['SELISIH NERACA',rupiah(d['difference'])]]
    return export_pdf('neraca','Laporan Neraca',_scope_subtitle(d, balance=True),['Uraian','Jumlah'],rows)


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
    as_of = _as_date(request)
    summary = calculate_depreciation_summary(as_of=as_of)
    rows = summary['rows']
    total_cost = summary['total_cost']
    total_year = summary['period_depreciation']
    total_accumulated = summary['accumulated_depreciation']
    total_book = summary['book_value']
    asset_count = summary['asset_count']
    return render(request, 'finance/depreciation.html', locals())


@login_required
@permission_required('finance.tax_reports')
def export_depreciation_pdf(request):
    as_of = _as_date(request)
    summary = calculate_depreciation_summary(as_of=as_of)
    rows = []
    for item in summary['rows']:
        asset = item['asset']
        rows.append([
            asset.code, asset.name, asset.get_fiscal_group_display(),
            rupiah(asset.total_cost), rupiah(item['period_depreciation']),
            rupiah(item['accumulated']), rupiah(item['book_value']),
        ])
    totals = [['', '', 'TOTAL', rupiah(summary['total_cost']),
               rupiah(summary['period_depreciation']),
               rupiah(summary['accumulated_depreciation']),
               rupiah(summary['book_value'])]]
    return export_pdf(
        'daftar_aset_penyusutan', 'Daftar Aset dan Penyusutan Fiskal',
        f"Posisi per {as_of.strftime('%d/%m/%Y')}",
        ['Kode','Nama Aset','Kelompok','Perolehan','Penyusutan Tahun Ini','Akumulasi','Nilai Buku'],
        rows, totals,
    )



ALLOWED_TRADE_DOCUMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx', '.xls', '.xlsx'}
MAX_TRADE_DOCUMENT_SIZE = 10 * 1024 * 1024

def _save_trade_documents(request, trade_account, payment=None):
    uploaded_files = request.FILES.getlist('documents')
    saved = 0
    rejected = []
    for uploaded in uploaded_files:
        from pathlib import Path
        extension = Path(uploaded.name).suffix.lower()
        if extension not in ALLOWED_TRADE_DOCUMENT_EXTENSIONS:
            rejected.append(f"{uploaded.name} (format tidak didukung)")
            continue
        if uploaded.size > MAX_TRADE_DOCUMENT_SIZE:
            rejected.append(f"{uploaded.name} (lebih dari 10 MB)")
            continue
        TradeDocument.objects.create(
            trade_account=trade_account, payment=payment, file=uploaded,
            original_name=uploaded.name[:255],
            description=(request.POST.get('document_description') or '').strip()[:180],
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        saved += 1
    if rejected:
        messages.warning(request, 'Sebagian dokumen tidak diunggah: ' + '; '.join(rejected))
    return saved

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
        if status == 'unpaid' and not (item.paid_amount <= 0 and item.outstanding_amount > 0):
            continue
        if status == 'partial' and not (item.paid_amount > 0 and item.outstanding_amount > 0):
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
        progress = Decimal('0')
        if item.original_amount and item.original_amount > 0:
            progress = min((item.paid_amount / item.original_amount) * Decimal('100'), Decimal('100'))
        rows.append({
            'item': item, 'paid': item.paid_amount, 'outstanding': item.outstanding_amount,
            'age_days': age_days, 'bucket': bucket, 'progress': progress,
        })
    return rows


def _trade_summary(rows):
    original = sum((r['item'].original_amount for r in rows), Decimal('0'))
    paid = sum((r['paid'] for r in rows), Decimal('0'))
    outstanding = sum((r['outstanding'] for r in rows), Decimal('0'))
    overdue = sum((r['outstanding'] for r in rows if r['item'].is_overdue), Decimal('0'))
    return original, paid, outstanding, overdue



def _set_payable_payment_status(obj, status, paid_amount, payment_date):
    """Set status utang secara eksplisit tanpa menghubungkannya ke pengeluaran operasional.

    Riwayat pembayaran lama dikonsolidasikan menjadi satu pembayaran penyesuaian.
    Dokumen pembayaran lama dipertahankan sebagai dokumen transaksi.
    """
    if obj.account_type != TradeAccount.PAYABLE:
        return

    status = (status or '').strip().lower()
    total = obj.original_amount or Decimal('0')
    if status == 'paid':
        target_paid = total
    elif status == 'partial':
        target_paid = paid_amount or Decimal('0')
        if target_paid <= 0 or target_paid >= total:
            raise ValueError('Untuk status Lunas Sebagian, jumlah dibayar harus lebih dari Rp0 dan lebih kecil dari nilai awal.')
    else:
        target_paid = Decimal('0')

    # Pertahankan file bukti lama dengan memindahkannya menjadi dokumen transaksi.
    TradeDocument.objects.filter(trade_account=obj, payment__isnull=False).update(payment=None)
    obj.payments.all().delete()

    if target_paid > 0:
        TradePayment.objects.create(
            trade_account=obj,
            payment_date=payment_date or timezone.localdate(),
            amount=target_paid,
            payment_method='Lainnya',
            document_number='PENYESUAIAN-STATUS',
            notes='Pembayaran hasil perubahan status utang melalui menu Edit Utang Usaha.',
        )

def _sale_from_trade_account(obj):
    """Ambil nota sumber dari penanda kartu piutang otomatis."""
    from .receivable_sync import AUTO_NOTE_PREFIX
    notes = obj.notes or ''
    for line in notes.splitlines():
        if line.startswith(AUTO_NOTE_PREFIX):
            try:
                return Sale.objects.filter(pk=int(line[len(AUTO_NOTE_PREFIX):].strip())).first()
            except (TypeError, ValueError):
                return None
    return None


def _sync_sale_status_from_receivable(obj):
    """Samakan status nota dengan saldo kartu piutang setelah cicilan berubah."""
    if obj.account_type != TradeAccount.RECEIVABLE:
        return
    sale = _sale_from_trade_account(obj)
    if not sale:
        return
    new_status = 'Lunas' if obj.outstanding_amount <= 0 else 'Belum Lunas'
    if sale.status != new_status:
        sale.status = new_status
        sale.save(update_fields=['status'])


@login_required
@permission_required('finance.tax_reports')
def receivables(request):
    # Nota lama yang masih belum lunas otomatis dibuatkan kartu piutang.
    from .receivable_sync import sync_open_sales
    sync_open_sales()
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
    today = timezone.localdate()
    month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    week_end = today + timedelta(days=7)
    partial_rows = [r for r in rows if r['paid'] > 0 and r['outstanding'] > 0]
    unpaid_rows = [r for r in rows if r['paid'] <= 0 and r['outstanding'] > 0]
    due_week_rows = [r for r in rows if r['outstanding'] > 0 and today <= r['item'].due_date <= week_end]
    due_month_rows = [r for r in rows if r['outstanding'] > 0 and today <= r['item'].due_date <= month_end]
    aging = {
        'not_due': sum((r['outstanding'] for r in rows if r['outstanding'] > 0 and not r['item'].is_overdue), Decimal('0')),
        'd1_30': sum((r['outstanding'] for r in rows if 1 <= r['age_days'] <= 30), Decimal('0')),
        'd31_60': sum((r['outstanding'] for r in rows if 31 <= r['age_days'] <= 60), Decimal('0')),
        'd61_90': sum((r['outstanding'] for r in rows if 61 <= r['age_days'] <= 90), Decimal('0')),
        'd90_plus': sum((r['outstanding'] for r in rows if r['age_days'] > 90), Decimal('0')),
    }
    overall_progress = (paid / original * Decimal('100')) if original else Decimal('0')
    return render(request, 'finance/trade_accounts.html', {
        'rows': rows, 'account_type': TradeAccount.PAYABLE, 'title': 'Utang Usaha',
        'partner_label': 'Supplier/Pemasok', 'original': original, 'paid': paid,
        'outstanding': outstanding, 'overdue': overdue,
        'partial_count': len(partial_rows), 'unpaid_count': len(unpaid_rows),
        'due_week_count': len(due_week_rows), 'due_week_amount': sum((r['outstanding'] for r in due_week_rows), Decimal('0')),
        'due_month_count': len(due_month_rows), 'due_month_amount': sum((r['outstanding'] for r in due_month_rows), Decimal('0')),
        'aging': aging, 'overall_progress': overall_progress,
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
        customer = None
        if account_type == TradeAccount.RECEIVABLE:
            customer = Customer.objects.filter(pk=request.POST.get('customer_id')).first()
        if account_type == TradeAccount.RECEIVABLE and customer is None:
            messages.error(request, 'Pilih pelanggan dari Master Pelanggan.')
        elif amount <= 0 or not transaction_date or not due_date:
            messages.error(request, 'Tanggal dan nilai transaksi wajib diisi dengan benar.')
        elif due_date < transaction_date:
            messages.error(request, 'Tanggal jatuh tempo tidak boleh sebelum tanggal transaksi.')
        else:
            obj = TradeAccount.objects.create(
                cycle=get_selected_cycle(request), account_type=account_type,
                transaction_date=transaction_date, due_date=due_date,
                document_number=request.POST.get('document_number','').strip(),
                customer=customer,
                partner_name=customer.name if customer else request.POST.get('partner_name','').strip(),
                description=request.POST.get('description','').strip(),
                original_amount=amount, notes=request.POST.get('notes','').strip(),
            )
            document_count = _save_trade_documents(request, obj)
            messages.success(request, f'{obj.get_account_type_display()} berhasil disimpan' + (f' dengan {document_count} dokumen.' if document_count else '.'))
            return redirect('finance:trade_detail', pk=obj.pk)
    return render(request, 'finance/trade_account_form.html', {
        'account_type': account_type,
        'title': 'Tambah Piutang Usaha' if account_type == TradeAccount.RECEIVABLE else 'Tambah Utang Usaha',
        'partner_label': 'Pelanggan' if account_type == TradeAccount.RECEIVABLE else 'Supplier/Pemasok',
        'customers': Customer.objects.order_by('name') if account_type == TradeAccount.RECEIVABLE else None,
    })


@login_required
@permission_required('finance.tax_reports')
def edit_trade_account(request, pk):
    obj = get_object_or_404(TradeAccount, pk=pk)
    if request.method == 'POST':
        amount = parse_rupiah(request.POST.get('original_amount'))
        transaction_date = parse_date(request.POST.get('transaction_date') or '')
        due_date = parse_date(request.POST.get('due_date') or '')
        customer = obj.customer
        if obj.account_type == TradeAccount.RECEIVABLE:
            customer = Customer.objects.filter(pk=request.POST.get('customer_id')).first()
        if obj.account_type == TradeAccount.RECEIVABLE and customer is None:
            messages.error(request, 'Pilih pelanggan dari Master Pelanggan.')
        elif obj.account_type != TradeAccount.PAYABLE and amount < obj.paid_amount:
            messages.error(request, 'Nilai awal tidak boleh lebih kecil dari total pembayaran yang sudah dicatat.')
        elif not transaction_date or not due_date or due_date < transaction_date:
            messages.error(request, 'Periksa kembali tanggal transaksi dan jatuh tempo.')
        else:
            obj.transaction_date=transaction_date; obj.due_date=due_date
            obj.document_number=request.POST.get('document_number','').strip()
            obj.customer = customer
            obj.partner_name = customer.name if customer else request.POST.get('partner_name','').strip()
            obj.description=request.POST.get('description','').strip()
            obj.original_amount=amount; obj.notes=request.POST.get('notes','').strip(); obj.save()
            if obj.account_type == TradeAccount.PAYABLE:
                try:
                    _set_payable_payment_status(
                        obj,
                        request.POST.get('payment_status'),
                        parse_rupiah(request.POST.get('paid_amount')),
                        parse_date(request.POST.get('status_payment_date') or ''),
                    )
                except ValueError as exc:
                    messages.error(request, str(exc))
                    return render(request, 'finance/trade_account_form.html', {
                        'obj':obj, 'account_type':obj.account_type,
                        'title':'Edit '+obj.get_account_type_display(),
                        'partner_label':'Supplier/Pemasok',
                        'current_paid': obj.paid_amount,
                    })
            document_count = _save_trade_documents(request, obj)
            messages.success(request, 'Data berhasil diperbarui' + (f' dan {document_count} dokumen ditambahkan.' if document_count else '.'))
            return redirect('finance:trade_detail', pk=obj.pk)
    return render(request, 'finance/trade_account_form.html', {
        'obj':obj, 'account_type':obj.account_type,
        'title':'Edit '+obj.get_account_type_display(),
        'partner_label':'Pelanggan' if obj.account_type == TradeAccount.RECEIVABLE else 'Supplier/Pemasok',
        'customers': Customer.objects.order_by('name') if obj.account_type == TradeAccount.RECEIVABLE else None,
        'current_paid': obj.paid_amount,
    })


@login_required
@permission_required('finance.tax_reports')
def trade_detail(request, pk):
    obj = get_object_or_404(
        TradeAccount.objects.prefetch_related('payments__documents', 'documents__uploaded_by'),
        pk=pk,
    )
    paid = obj.paid_amount
    outstanding = obj.outstanding_amount
    payment_progress = (paid / obj.original_amount * Decimal('100')) if obj.original_amount else Decimal('0')
    all_documents = list(obj.documents.select_related('payment', 'uploaded_by').all())
    account_documents = [doc for doc in all_documents if doc.payment_id is None]
    payment_documents = [doc for doc in all_documents if doc.payment_id is not None]
    return render(request, 'finance/trade_account_detail.html', {
        'obj': obj, 'payments': obj.payments.all(), 'paid': paid,
        'outstanding': outstanding, 'payment_progress': payment_progress,
        'account_documents': account_documents,
        'payment_documents': payment_documents,
        'all_documents': all_documents,
        'document_count': len(all_documents),
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
        payment = TradePayment.objects.create(
            trade_account=obj, payment_date=payment_date, amount=amount,
            payment_method=request.POST.get('payment_method','Transfer'),
            document_number=request.POST.get('document_number','').strip(),
            notes=request.POST.get('notes','').strip(),
        )
        document_count = _save_trade_documents(request, obj, payment=payment)
        _sync_sale_status_from_receivable(obj)
        messages.success(request, 'Pembayaran sebagian berhasil dicatat' + (f' dengan {document_count} dokumen.' if document_count else '.') + f' Sisa saldo: {rupiah(obj.outstanding_amount)}.')
    return redirect('finance:trade_detail', pk=obj.pk)


@login_required
@permission_required('finance.tax_reports')
@require_POST
def delete_trade_payment(request, pk):
    payment = get_object_or_404(TradePayment, pk=pk)
    account_pk = payment.trade_account_id
    account = payment.trade_account
    payment.delete()
    _sync_sale_status_from_receivable(account)
    messages.success(request, 'Pembayaran berhasil dihapus dan saldo utang/piutang diperbarui.')
    return redirect('finance:trade_detail', pk=account_pk)


@login_required
@permission_required('finance.tax_reports')
@require_POST
def upload_trade_documents(request, pk):
    obj = get_object_or_404(TradeAccount, pk=pk)
    count = _save_trade_documents(request, obj)
    if count:
        messages.success(request, f'{count} dokumen berhasil diunggah.')
    elif not request.FILES.getlist('documents'):
        messages.error(request, 'Pilih minimal satu dokumen untuk diunggah.')
    return redirect('finance:trade_detail', pk=obj.pk)


@login_required
@permission_required('finance.tax_reports')
def preview_trade_document(request, pk):
    document = get_object_or_404(TradeDocument.objects.select_related('trade_account'), pk=pk)
    if not document.file:
        raise Http404('File tidak tersedia.')
    try:
        file_handle = document.file.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('File tidak ditemukan pada penyimpanan.')
    filename = document.original_name or Path(document.file.name).name
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    response = FileResponse(file_handle, as_attachment=False, filename=filename, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{filename.replace(chr(34), "")}"'
    return response


@login_required
@permission_required('finance.tax_reports')
def download_trade_document(request, pk):
    document = get_object_or_404(TradeDocument.objects.select_related('trade_account'), pk=pk)
    if not document.file:
        raise Http404('File tidak tersedia.')
    try:
        file_handle = document.file.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('File tidak ditemukan pada penyimpanan.')
    filename = document.original_name or Path(document.file.name).name
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    return FileResponse(file_handle, as_attachment=True, filename=filename, content_type=content_type)


@login_required
@permission_required('finance.tax_reports')
@require_POST
def delete_trade_document(request, pk):
    document = get_object_or_404(TradeDocument, pk=pk)
    account_pk = document.trade_account_id
    storage = document.file.storage
    file_name = document.file.name
    document.delete()
    if file_name and storage.exists(file_name):
        storage.delete(file_name)
    messages.success(request, 'Dokumen berhasil dihapus.')
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
