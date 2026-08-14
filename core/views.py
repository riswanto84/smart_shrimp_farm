from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required, has_permission
from ponds.models import Pond
from operations.models import DailyParameter, SamplingRecord, Harvest, SiphonRecord
from operations.services.biomass import calculate_index_biomass_snapshot
from sales.models import Sale, SaleItem
from finance.models import OperationalExpense, TradeAccount
from finance.services.profit_loss import calculate_profit_loss
from finance.services.depreciation import calculate_depreciation_summary
from finance.services.final_cycle_profit import calculate_final_cycle_profit
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import math
from chat_ai.services import ollama_health
from cultivation.utils import filter_selected_cycle, get_selected_cycle
from core.weather_service import get_farm_weather


def _is_total_harvest_type(value):
    """Kenali variasi label panen total/final tanpa mengubah struktur database."""
    text = str(value or '').strip().lower().replace('_', ' ').replace('-', ' ')
    return text in {'total', 'final', 'panen total', 'panen final', 'selesai'}


def _parse_harvest_size(value):
    """Ambil angka size pertama dari teks seperti '118', 'size 50', atau '50/55'."""
    import re
    match = re.search(r'\d+(?:[.,]\d+)?', str(value or ''))
    if not match:
        return Decimal('0')
    try:
        return Decimal(match.group(0).replace(',', '.'))
    except Exception:
        return Decimal('0')

def home(request):
    # Halaman company profile/public home dinonaktifkan.
    # Root aplikasi langsung diarahkan ke halaman login admin.
    return redirect('accounts:login')
@login_required
@permission_required('dashboard')
def dashboard(request):
    ponds = Pond.objects.all()
    # Data keuangan dashboard hanya dihitung dan dikirim ke browser untuk role
    # yang memang memiliki izin modul keuangan. Teknisi tetap mendapatkan
    # dashboard operasional tanpa angka omzet, biaya, laba, utang, pajak, dll.
    can_view_financial_dashboard = has_permission(request.user, 'finance.profit_loss')

    # KPI keuangan hanya untuk role yang memiliki izin keuangan.
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    sales_total = Decimal('0')
    yesterday_sales_total = Decimal('0')
    sales_change_percent = Decimal('0')
    sales_change_state = 'neutral'
    sales_change_text = 'Data keuangan tidak ditampilkan untuk role ini'

    expense_total = Decimal('0')
    production_operational_total = Decimal('0')
    payroll_total = Decimal('0')
    depreciation_total = Decimal('0')
    depreciation_asset_count = 0
    depreciation_book_value = Decimal('0')
    administration_total = Decimal('0')
    profit_loss_total = Decimal('0')
    profit_margin_percent = Decimal('0')
    profit_loss_status = '—'

    valid_sales = Sale.objects.none()
    finance_result = {}
    if can_view_financial_dashboard:
        valid_sales = filter_selected_cycle(
            request,
            Sale.objects.exclude(status__in=['Gagal', 'Expired', 'Dibatalkan', 'Refund']),
        )
        sales_total = valid_sales.aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
        yesterday_sales_total = (
            valid_sales.filter(date__date=yesterday).aggregate(s=Sum('total_amount'))['s']
            or Decimal('0')
        )

        if yesterday_sales_total > 0:
            sales_change_percent = (
                (sales_total - yesterday_sales_total) / yesterday_sales_total * Decimal('100')
            ).quantize(Decimal('0.1'))
            if sales_change_percent > 0:
                sales_change_state = 'up'
                sales_change_text = f'Naik {abs(sales_change_percent)}% dari kemarin'
            elif sales_change_percent < 0:
                sales_change_state = 'down'
                sales_change_text = f'Turun {abs(sales_change_percent)}% dari kemarin'
            else:
                sales_change_state = 'neutral'
                sales_change_text = 'Tidak berubah dari kemarin'
        elif sales_total > 0:
            sales_change_percent = None
            sales_change_state = 'up'
            sales_change_text = 'Baru ada omzet hari ini'
        else:
            sales_change_text = 'Belum ada omzet hari ini maupun kemarin'

        selected_cycle = get_selected_cycle(request)
        finance_result = calculate_profit_loss(cycle=selected_cycle, date_to=today)
        sales_total = finance_result['revenue']
        expense_total = finance_result['expense_total']
        category_totals = finance_result['category_totals']
        payroll_total = category_totals.get('Tenaga Kerja', Decimal('0'))
        depreciation_total = category_totals.get('Penyusutan', Decimal('0'))
        depreciation_summary = finance_result.get('depreciation_summary') or calculate_depreciation_summary(as_of=today)
        depreciation_asset_count = depreciation_summary['asset_count']
        depreciation_book_value = depreciation_summary['book_value']
        administration_total = category_totals.get('Administrasi', Decimal('0'))
        production_operational_total = max(
            expense_total - payroll_total - depreciation_total - administration_total,
            Decimal('0'),
        )
        profit_loss_total = finance_result['profit']
        profit_margin_percent = (
            (profit_loss_total / sales_total) * Decimal('100')
            if sales_total > 0
            else Decimal('0')
        )
        if profit_loss_total > 0:
            profit_loss_status = 'Laba'
        elif profit_loss_total < 0:
            profit_loss_status = 'Rugi'
        else:
            profit_loss_status = 'Impas'

    # Siklus tetap tersedia untuk dashboard operasional.
    selected_cycle = get_selected_cycle(request)

    # Ringkasan utang usaha hanya untuk role yang memiliki izin keuangan.
    unpaid_payables = []
    unpaid_payables_total = Decimal('0')
    unpaid_payables_count = 0
    due_this_month = []
    due_this_month_total = Decimal('0')
    due_this_month_count = 0
    nearest_due_payable = None
    if can_view_financial_dashboard:
        payable_accounts = list(
            TradeAccount.objects.filter(account_type=TradeAccount.PAYABLE)
            .prefetch_related('payments')
            .order_by('due_date', 'id')
        )
        unpaid_payables = [account for account in payable_accounts if account.outstanding_amount > 0]
        unpaid_payables_total = sum(
            (account.outstanding_amount for account in unpaid_payables), Decimal('0')
        )
        unpaid_payables_count = len(unpaid_payables)

        month_start = today.replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
        due_this_month = [
            account for account in unpaid_payables
            if month_start <= account.due_date < next_month_start
        ]
        due_this_month_total = sum(
            (account.outstanding_amount for account in due_this_month), Decimal('0')
        )
        due_this_month_count = len(due_this_month)
        nearest_due_payable = due_this_month[0] if due_this_month else None

    # Realisasi panen riil diambil langsung dari menu Panen pada siklus terpilih.
    harvest_qs = filter_selected_cycle(
        request,
        Harvest.objects.select_related('pond').order_by('-date', '-id'),
    )
    harvest_total_kg = harvest_qs.aggregate(total=Sum('total_kg'))['total'] or Decimal('0')
    harvest_total_ton = harvest_total_kg / Decimal('1000')
    harvest_count = harvest_qs.count()
    latest_harvests = list(harvest_qs[:8])

    # Ringkasan panen parsial pada dashboard. Panen total/final tidak masuk
    # ke angka ini agar pengguna dapat membedakan hasil parsial dan panen akhir.
    partial_harvests = [
        harvest for harvest in harvest_qs
        if not _is_total_harvest_type(harvest.harvest_type)
    ]
    partial_harvest_total_kg = sum(
        (Decimal(str(harvest.total_kg or 0)) for harvest in partial_harvests),
        Decimal('0'),
    )
    partial_harvest_total_ton = partial_harvest_total_kg / Decimal('1000')
    partial_harvest_count = len(partial_harvests)
    partial_harvest_pond_count = len({harvest.pond_id for harvest in partial_harvests})
    latest_partial_harvest = partial_harvests[0] if partial_harvests else None

    partial_by_pond_map = {}
    for harvest in partial_harvests:
        row = partial_by_pond_map.setdefault(harvest.pond_id, {
            'pond': harvest.pond,
            'total_kg': Decimal('0'),
            'count': 0,
            'latest_date': harvest.date,
            'latest_size': harvest.size_text or '-',
        })
        row['total_kg'] += Decimal(str(harvest.total_kg or 0))
        row['count'] += 1
        if harvest.date >= row['latest_date']:
            row['latest_date'] = harvest.date
            row['latest_size'] = harvest.size_text or '-'
    partial_harvest_by_pond = sorted(
        partial_by_pond_map.values(),
        key=lambda row: (row['total_kg'], row['latest_date']),
        reverse=True,
    )
    for row in partial_harvest_by_pond:
        row['total_ton'] = row['total_kg'] / Decimal('1000')

    # Harga jual dan size riil dipadankan dari detail nota penjualan yang
    # menunjuk ke record panen. Tidak memerlukan perubahan model/migrasi.
    latest_harvest_ids = [harvest.id for harvest in latest_harvests]
    linked_sale_items = (
        SaleItem.objects.select_related('sale', 'harvest')
        .filter(
            harvest_id__in=latest_harvest_ids,
            sale__in=valid_sales,
        )
        .order_by('sale__date', 'id')
    )
    sale_items_by_harvest = {}
    for item in linked_sale_items:
        sale_items_by_harvest.setdefault(item.harvest_id, []).append(item)

    latest_harvest_rows = []
    for harvest in latest_harvests:
        items = sale_items_by_harvest.get(harvest.id, [])
        sold_kg = sum((item.weight_kg or Decimal('0') for item in items), Decimal('0'))
        sold_subtotal = sum((item.subtotal or Decimal('0') for item in items), Decimal('0'))
        weighted_price = sold_subtotal / sold_kg if sold_kg > 0 else Decimal('0')
        sale_sizes = []
        for item in items:
            size = (item.size_text or '').strip()
            if size and size not in sale_sizes:
                sale_sizes.append(size)
        latest_harvest_rows.append({
            'harvest': harvest,
            'actual_size': ' / '.join(sale_sizes) or harvest.size_text or '-',
            'sold_kg': sold_kg,
            'price_per_kg': weighted_price,
            'subtotal': sold_subtotal,
            'has_sale': bool(items),
        })

    latest_harvest_size = latest_harvest_rows[0]['actual_size'] if latest_harvest_rows else '-'
    latest_harvest_price = latest_harvest_rows[0]['price_per_kg'] if latest_harvest_rows else Decimal('0')

    target_harvest_ton = Decimal(str(getattr(selected_cycle, 'target_biomass_ton', 0) or 0))
    target_harvest_kg = target_harvest_ton * Decimal('1000')
    if target_harvest_kg > 0:
        harvest_progress_percent = min(
            Decimal('100'),
            (harvest_total_kg / target_harvest_kg * Decimal('100')).quantize(Decimal('0.1')),
        )
        harvest_remaining_kg = max(Decimal('0'), target_harvest_kg - harvest_total_kg)
    else:
        harvest_progress_percent = Decimal('0')
        harvest_remaining_kg = Decimal('0')

    # Omzet siklus dan harga jual rata-rata memakai transaksi valid pada siklus yang sama.
    cycle_sales_total = valid_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    cycle_sales_kg = valid_sales.aggregate(total=Sum('total_kg'))['total'] or Decimal('0')
    average_sale_price = (cycle_sales_total / cycle_sales_kg) if cycle_sales_kg > 0 else Decimal('0')

    # Ringkasan grafik panen berdasarkan tanggal, maksimal 10 tanggal terbaru.
    harvest_daily_rows = list(
        harvest_qs.values('date').annotate(total_kg=Sum('total_kg')).order_by('-date')[:10]
    )
    harvest_daily_rows.reverse()
    max_daily_harvest = max((row['total_kg'] or Decimal('0') for row in harvest_daily_rows), default=Decimal('0'))
    harvest_chart = []
    for row in harvest_daily_rows:
        total_kg = row['total_kg'] or Decimal('0')
        width_percent = float(total_kg / max_daily_harvest * Decimal('100')) if max_daily_harvest > 0 else 0
        harvest_chart.append({
            'date': row['date'],
            'total_kg': total_kg,
            'width_percent': round(width_percent, 2),
        })

    # Parameter air aktual: tidak pernah memakai angka fallback/dummy.
    parameter_qs = filter_selected_cycle(
        request,
        DailyParameter.objects.select_related('pond').order_by('-date', '-created_at', '-id'),
    )
    latest = parameter_qs.first()

    temperature_records = []
    temperature_points = ''
    if latest:
        temperature_records = list(
            parameter_qs.filter(pond=latest.pond, temperature__isnull=False)
            .order_by('-date', '-created_at', '-id')[:7]
        )
        temperature_records.reverse()
        values = [float(item.temperature) for item in temperature_records]
        if values:
            width, height, padding = 600.0, 180.0, 12.0
            minimum, maximum = min(values), max(values)
            span = maximum - minimum or 1.0
            denominator = max(len(values) - 1, 1)
            points = []
            for index, value in enumerate(values):
                x = padding + index * ((width - 2 * padding) / denominator)
                y = padding + (maximum - value) * ((height - 2 * padding) / span)
                points.append(f'{x:.1f},{y:.1f}')
            temperature_points = ' '.join(points)

    # Produksi aktif memakai sampling terbaru per kolam, bukan hanya satu tanggal
    # global. Kolam yang sudah panen total/final dikeluarkan dari biomassa dan
    # proyeksi. Panen parsial setelah sampling mengurangi biomassa dan populasi.
    sampling_qs = filter_selected_cycle(
        request,
        SamplingRecord.objects.select_related('pond').order_by('-date', '-created_at', '-id'),
    )
    latest_sampling_date = sampling_qs.values_list('date', flat=True).first()
    selected_sampling_records = {}
    for record in sampling_qs:
        if record.pond_id not in selected_sampling_records:
            selected_sampling_records[record.pond_id] = record

    harvests_by_pond = {}
    harvest_total_by_pond = {}
    for harvest in harvest_qs.order_by('date', 'id'):
        harvests_by_pond.setdefault(harvest.pond_id, []).append(harvest)
        harvest_total_by_pond[harvest.pond_id] = (
            harvest_total_by_pond.get(harvest.pond_id, Decimal('0'))
            + Decimal(str(harvest.total_kg or 0))
        )

    completed_pond_ids = set()
    for pond in ponds:
        record = selected_sampling_records.get(pond.id)
        pond_harvests = harvests_by_pond.get(pond.id, [])
        latest_total = next((h for h in reversed(pond_harvests) if _is_total_harvest_type(h.harvest_type)), None)
        total_after_latest_sample = bool(
            latest_total and (record is None or latest_total.date >= record.date)
        )
        if pond.status == 'Panen' or total_after_latest_sample:
            completed_pond_ids.add(pond.id)

    production_items = []
    production_index_items = []
    # Mortalitas siphon setelah sampling terakhir ikut mengurangi populasi dan biomassa tersisa.
    siphon_qs = filter_selected_cycle(
        request,
        SiphonRecord.objects.select_related('pond').order_by('date', 'id'),
    )
    siphons_by_pond = {}
    for siphon in siphon_qs:
        siphons_by_pond.setdefault(siphon.pond_id, []).append(siphon)

    production_total_kg = 0.0
    production_index_total_kg = Decimal('0')
    active_projection_records = []

    # Target panen size 30 = ABW 33,33 gram/ekor.
    target_size_30 = Decimal('30')
    target_abw_30 = Decimal('1000') / target_size_30
    doc120_target = 120
    doc120_total_kg = Decimal('0')

    for pond in ponds:
        record = selected_sampling_records.get(pond.id)
        stocking_count = int(record.stocking_count or 0) if record else 0
        area_m2 = float(pond.area_m2 or 0)
        pond.dashboard_stocking_count = stocking_count
        pond.dashboard_stocking_density = (stocking_count / area_m2) if stocking_count and area_m2 else None
        pond.dashboard_stocking_date = record.date if record else None
        pond.dashboard_doc = int(record.doc or 0) if record else None
        pond.dashboard_is_completed = pond.id in completed_pond_ids
        pond.dashboard_real_harvest_kg = harvest_total_by_pond.get(pond.id, Decimal('0'))
        pond.dashboard_real_harvest_ton = (
            pond.dashboard_real_harvest_kg / Decimal('1000')
        ).quantize(Decimal('0.01'))
        pond.dashboard_size30_date = None
        pond.dashboard_size30_days = None
        pond.dashboard_size30_status = 'Belum ada data sampling'
        pond.dashboard_size30_abw = target_abw_30
        pond.dashboard_doc120_abw = None
        pond.dashboard_doc120_size = None
        pond.dashboard_doc120_biomass_kg = None
        pond.dashboard_doc120_biomass_ton = None
        pond.dashboard_doc120_days = None
        pond.dashboard_doc120_status = 'Belum ada data sampling'
        pond.dashboard_remaining_biomass_kg = Decimal('0')
        pond.dashboard_partial_harvest_kg = Decimal('0')

        if not record:
            continue

        current_abw = Decimal(str(record.abw_g or 0))
        adg_actual = Decimal(str(record.adg_weekly or 0))
        population_fr = int(record.population or 0)
        sampling_biomass = Decimal(str(record.biomass_kg or 0))
        sampling_biomass_index = Decimal(str(record.biomass_index_kg or 0))

        # Hanya panen pada tanggal setelah sampling yang mengurangi snapshot terbaru.
        # Transaksi pada tanggal yang sama tidak dikurangi untuk mencegah hitung ganda
        # ketika sampling dilakukan setelah panen pada hari yang sama.
        partial_harvests = [
            h for h in harvests_by_pond.get(pond.id, [])
            if h.date > record.date and not _is_total_harvest_type(h.harvest_type)
        ]
        partial_kg = sum((Decimal(str(h.total_kg or 0)) for h in partial_harvests), Decimal('0'))
        # Udang mati pada tanggal setelah sampling terakhir mengurangi estimasi sisa.
        # Catatan siphon pada tanggal yang sama tidak dihitung ulang karena urutan jam
        # kejadian belum tersimpan di database.
        dead_after_sampling = sum(
            int(s.dead_count or 0)
            for s in siphons_by_pond.get(pond.id, [])
            if s.date > record.date
        )
        mortality_biomass_kg = (Decimal(dead_after_sampling) * current_abw / Decimal('1000')) if current_abw > 0 else Decimal('0')
        remaining_biomass = max(Decimal('0'), sampling_biomass - partial_kg - mortality_biomass_kg)
        remaining_biomass_index = max(
            Decimal('0'),
            sampling_biomass_index - partial_kg - mortality_biomass_kg,
        )
        remaining_population = max(0, population_fr - dead_after_sampling)
        for h in partial_harvests:
            size = _parse_harvest_size(h.size_text)
            if size > 0:
                harvested_population = int(Decimal(str(h.total_kg or 0)) * size)
                remaining_population = max(0, remaining_population - harvested_population)
        # Jika size panen tidak tersedia, kurangi populasi secara proporsional
        # terhadap biomassa agar proyeksi tidak tetap memakai populasi sebelum panen.
        if partial_kg > 0 and population_fr > 0 and remaining_population == population_fr and sampling_biomass > 0:
            ratio = remaining_biomass / sampling_biomass
            remaining_population = max(0, int(Decimal(population_fr) * ratio))

        pond.dashboard_partial_harvest_kg = partial_kg
        pond.dashboard_remaining_biomass_kg = remaining_biomass
        pond.dashboard_remaining_biomass_index_kg = remaining_biomass_index

        if pond.id in completed_pond_ids:
            pond.dashboard_size30_status = 'Kolam sudah selesai panen'
            pond.dashboard_doc120_status = 'Tidak dihitung: panen total/selesai'
            continue

        # Biomassa produksi hanya menunjukkan yang masih berada di kolam.
        # Carrying Capacity (CC) mengikuti rumus teknisi tambak:
        # CC (kg/m²) = estimasi biomassa tersisa (kg) / luas kolam (m²).
        # Luas yang digunakan adalah Pond.area_m2. Jika luas belum diisi, CC = 0.
        pond_area = Decimal(str(pond.area_m2 or 0))
        cc_fr = (
            remaining_biomass / pond_area
            if pond_area > 0 else Decimal('0')
        )
        cc_index = (
            remaining_biomass_index / pond_area
            if pond_area > 0 else Decimal('0')
        )
        pond.dashboard_cc_fr = cc_fr.quantize(Decimal('0.01'))
        pond.dashboard_cc_index = cc_index.quantize(Decimal('0.01'))

        production_items.append({
            'pond': pond,
            'biomass_kg': float(remaining_biomass),
            'biomass_ton': float(remaining_biomass / Decimal('1000')),
            'cc': float(cc_fr),
        })
        production_index_items.append({
            'pond': pond,
            'biomass_kg': float(remaining_biomass_index),
            'biomass_ton': float(remaining_biomass_index / Decimal('1000')),
            'cc': float(cc_index),
        })
        production_total_kg += float(remaining_biomass)
        production_index_total_kg += remaining_biomass_index
        active_projection_records.append(record)

        if current_abw >= target_abw_30:
            pond.dashboard_size30_date = record.date
            pond.dashboard_size30_days = 0
            pond.dashboard_size30_status = 'Target size 30 telah tercapai'
        elif current_abw > 0 and adg_actual > 0:
            remaining = (target_abw_30 - current_abw) / adg_actual
            days_needed = max(0, math.ceil(float(remaining)))
            pond.dashboard_size30_days = days_needed
            pond.dashboard_size30_date = record.date + timedelta(days=days_needed)
            pond.dashboard_size30_status = 'Proyeksi berdasarkan ADG aktual'
        elif current_abw > 0:
            pond.dashboard_size30_status = 'ADG aktual belum tersedia'

        current_doc = int(record.doc or 0)
        remaining_doc_days = max(doc120_target - current_doc, 0)
        pond.dashboard_doc120_days = remaining_doc_days
        if current_abw > 0 and adg_actual > 0 and remaining_population > 0:
            projected_abw = current_abw + (adg_actual * Decimal(remaining_doc_days))
            projected_size = (Decimal('1000') / projected_abw) if projected_abw > 0 else Decimal('0')
            projected_biomass = Decimal(remaining_population) * projected_abw / Decimal('1000')
            pond.dashboard_doc120_abw = projected_abw.quantize(Decimal('0.01'))
            pond.dashboard_doc120_size = projected_size.quantize(Decimal('0.01'))
            pond.dashboard_doc120_biomass_kg = projected_biomass.quantize(Decimal('0.01'))
            pond.dashboard_doc120_biomass_ton = (projected_biomass / Decimal('1000')).quantize(Decimal('0.01'))
            pond.dashboard_doc120_status = 'Proyeksi biomassa tersisa setelah panen parsial'
            doc120_total_kg += projected_biomass
        elif remaining_population <= 0:
            pond.dashboard_doc120_status = 'Populasi tersisa tidak tersedia'
        elif adg_actual <= 0:
            pond.dashboard_doc120_status = 'ADG aktual belum tersedia'

    # Sumber tunggal biomassa INDEX untuk Dashboard dan Neraca.
    # Nilai hasil perhitungan lama di atas ditimpa secara sengaja agar semua
    # modul menampilkan angka yang identik.
    index_snapshot = calculate_index_biomass_snapshot(as_of=today, ponds=ponds)
    production_index_items = []
    production_index_total_kg = index_snapshot['total_kg']
    index_by_pond = index_snapshot['by_pond']
    for pond in ponds:
        result = index_by_pond.get(pond.id)
        if not result:
            pond.dashboard_remaining_biomass_index_kg = Decimal('0')
            pond.dashboard_cc_index = Decimal('0')
            continue
        pond.dashboard_remaining_biomass_index_kg = result.biomass_index_kg
        pond.dashboard_index_method = 'INDEX'
        pond.dashboard_index_sampling_kg = result.sampling_biomass_index_kg
        pond.dashboard_index_growth_kg = result.growth_index_kg
        pond.dashboard_index_partial_harvest_kg = result.partial_harvest_kg
        pond.dashboard_index_mortality_kg = result.mortality_index_kg
        pond_area = Decimal(str(pond.area_m2 or 0))
        cc_index = result.biomass_index_kg / pond_area if pond_area > 0 else Decimal('0')
        pond.dashboard_cc_index = cc_index.quantize(Decimal('0.01'))
        production_index_items.append({
            'pond': pond,
            'biomass_kg': float(result.biomass_index_kg),
            'biomass_ton': float(result.biomass_index_kg / Decimal('1000')),
            'cc': float(cc_index),
            'method': 'INDEX',
        })

    production_total_ton = production_total_kg / 1000
    production_index_total_ton = production_index_total_kg / Decimal('1000')
    doc120_total_ton = doc120_total_kg / Decimal('1000')
    doc120_normal_ton = doc120_total_ton * Decimal('0.95')
    doc120_conservative_ton = doc120_total_ton * Decimal('0.90')
    total_cycle_potential_ton = harvest_total_ton + doc120_total_ton
    active_pond_count = len([p for p in ponds if p.id not in completed_pond_ids and p.id in selected_sampling_records])
    palette = ['#2d7ff9', '#f59e0b', '#22c55e', '#ef4444', '#8b5cf6', '#06b6d4', '#64748b']
    gradient_parts = []
    cumulative = 0.0
    for index, item in enumerate(production_items):
        item['color'] = palette[index % len(palette)]
        percentage = (item['biomass_kg'] / production_total_kg * 100) if production_total_kg else 0
        start_pct = cumulative
        cumulative += percentage
        gradient_parts.append(f"{item['color']} {start_pct:.3f}% {cumulative:.3f}%")
    production_gradient = ','.join(gradient_parts) if gradient_parts else '#e2e8f0 0 100%'

    index_gradient_parts = []
    index_cumulative = 0.0
    production_index_total_float = float(production_index_total_kg)
    for index, item in enumerate(production_index_items):
        item['color'] = palette[index % len(palette)]
        percentage = (item['biomass_kg'] / production_index_total_float * 100) if production_index_total_float else 0
        start_pct = index_cumulative
        index_cumulative += percentage
        index_gradient_parts.append(f"{item['color']} {start_pct:.3f}% {index_cumulative:.3f}%")
    production_index_gradient = ','.join(index_gradient_parts) if index_gradient_parts else '#e2e8f0 0 100%'

    latest_temperature = latest.temperature if latest else None
    latest_ph = None
    latest_do = None
    latest_salinity = latest.salinity if latest else None
    latest_transparency = None
    if latest:
        latest_ph = latest.ph_evening if latest.ph_evening is not None else latest.ph_morning
        latest_do = latest.do_night if latest.do_night is not None else latest.do_morning
        latest_transparency = (
            latest.transparency_evening
            if latest.transparency_evening is not None
            else latest.transparency_morning
            if latest.transparency_morning is not None
            else latest.transparency
        )

    ollama_status = ollama_health(timeout=2)
    # Ambil cuaca langsung pada view dashboard. Nilai context view mengungguli
    # context processor sehingga dashboard selalu memakai service cuaca terbaru.
    live_weather = get_farm_weather()

    # Estimasi laba akhir siklus: omzet berjalan + nilai Biomassa Index dengan
    # harga jual rata-rata aktual, dikurangi biaya berjalan, saldo utang, dan
    # PPh Final 0,5%. Parameter ?simulation_price= dapat dipakai untuk simulasi.
    simulated_price = request.GET.get('simulation_price')
    final_cycle_profit = None
    if can_view_financial_dashboard:
        final_cycle_profit = calculate_final_cycle_profit(
            cycle=selected_cycle, as_of=today, simulated_price=simulated_price
        )

    context = {
        'ponds': ponds,
        'sales_total': sales_total,
        'yesterday_sales_total': yesterday_sales_total,
        'sales_change_percent': sales_change_percent,
        'sales_change_state': sales_change_state,
        'sales_change_text': sales_change_text,
        'expense_total': expense_total,
        'production_operational_total': production_operational_total,
        'payroll_total': payroll_total,
        'depreciation_total': depreciation_total,
        'depreciation_asset_count': depreciation_asset_count,
        'depreciation_book_value': depreciation_book_value,
        'administration_total': administration_total,
        'profit_loss_total': profit_loss_total,
        'profit_margin_percent': profit_margin_percent,
        'profit_loss_status': profit_loss_status,
        'unpaid_payables_total': unpaid_payables_total,
        'unpaid_payables_count': unpaid_payables_count,
        'due_this_month_total': due_this_month_total,
        'due_this_month_count': due_this_month_count,
        'nearest_due_payable': nearest_due_payable,
        'selected_cycle': selected_cycle,
        'harvest_total_kg': harvest_total_kg,
        'harvest_total_ton': harvest_total_ton,
        'harvest_count': harvest_count,
        'partial_harvest_total_kg': partial_harvest_total_kg,
        'partial_harvest_total_ton': partial_harvest_total_ton,
        'partial_harvest_count': partial_harvest_count,
        'partial_harvest_pond_count': partial_harvest_pond_count,
        'latest_partial_harvest': latest_partial_harvest,
        'partial_harvest_by_pond': partial_harvest_by_pond,
        'latest_harvests': latest_harvests,
        'latest_harvest_rows': latest_harvest_rows,
        'latest_harvest_size': latest_harvest_size,
        'latest_harvest_price': latest_harvest_price,
        'target_harvest_ton': target_harvest_ton,
        'target_harvest_kg': target_harvest_kg,
        'harvest_progress_percent': harvest_progress_percent,
        'harvest_remaining_kg': harvest_remaining_kg,
        'cycle_sales_total': cycle_sales_total,
        'cycle_sales_kg': cycle_sales_kg,
        'average_sale_price': average_sale_price,
        'harvest_chart': harvest_chart,
        'latest': latest,
        'latest_temperature': latest_temperature,
        'latest_ph': latest_ph,
        'latest_do': latest_do,
        'latest_salinity': latest_salinity,
        'latest_transparency': latest_transparency,
        'temperature_records': temperature_records,
        'temperature_points': temperature_points,
        'production_items': production_items,
        'production_index_items': production_index_items,
        'production_total_kg': production_total_kg,
        'production_total_ton': production_total_ton,
        'production_index_total_kg': production_index_total_kg,
        'production_index_total_ton': production_index_total_ton,
        'production_gradient': production_gradient,
        'production_index_gradient': production_index_gradient,
        'active_pond_count': active_pond_count,
        'completed_pond_count': len(completed_pond_ids),
        'total_cycle_potential_ton': total_cycle_potential_ton,
        'latest_sampling_date': latest_sampling_date,
        'doc120_target': doc120_target,
        'doc120_total_ton': doc120_total_ton,
        'doc120_normal_ton': doc120_normal_ton,
        'doc120_conservative_ton': doc120_conservative_ton,
        'ollama_status': ollama_status,
        'live_weather': live_weather,
        'final_cycle_profit': final_cycle_profit,
        'can_view_financial_dashboard': can_view_financial_dashboard,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@require_POST
@permission_required('dashboard')
def mark_notifications_read(request):
    """Tandai notifikasi aktif sebagai sudah dibaca untuk session user saat ini."""
    key = request.POST.get('key', '').strip()
    if key:
        request.session['ssf_notifications_read_key'] = key
        request.session.modified = True
    return JsonResponse({'ok': True})


@login_required
@permission_required('dashboard')
def weather_status_api(request):
    """Status cuaca aktual dari proses web/Gunicorn.

    Endpoint ini juga menjadi mekanisme pemulihan otomatis jika render awal
    belum memperoleh data. Gunakan ?refresh=1 untuk memaksa request API.
    """
    force_refresh = request.GET.get('refresh') == '1'
    result = dict(get_farm_weather(force_refresh=force_refresh))
    for field in ('updated_at', 'checked_at'):
        value = result.get(field)
        if value is not None:
            try:
                result[field] = value.isoformat()
            except AttributeError:
                result[field] = str(value)
    return JsonResponse(result)


@login_required
@permission_required('dashboard')
def ollama_status_api(request):
    """Status Ollama aktual untuk refresh dashboard tanpa reload penuh."""
    return JsonResponse(ollama_health(timeout=2))
