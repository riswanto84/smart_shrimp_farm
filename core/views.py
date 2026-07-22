from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from ponds.models import Pond
from operations.models import DailyParameter, SamplingRecord, Harvest
from sales.models import Sale, SaleItem
from finance.models import OperationalExpense
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

    # KPI omzet menggunakan tanggal lokal aplikasi (WIB), bukan total seluruh
    # siklus. Transaksi gagal, kedaluwarsa, dibatalkan, dan refund tidak dihitung.
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    valid_sales = filter_selected_cycle(
        request,
        Sale.objects.exclude(status__in=['Gagal', 'Expired', 'Dibatalkan', 'Refund']),
    )
    sales_total = (
        valid_sales.filter(date__date=today).aggregate(s=Sum('total_amount'))['s']
        or Decimal('0')
    )
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
        # Persentase tidak terdefinisi jika pembanding kemarin bernilai nol.
        sales_change_percent = None
        sales_change_state = 'up'
        sales_change_text = 'Baru ada omzet hari ini'
    else:
        sales_change_percent = Decimal('0')
        sales_change_state = 'neutral'
        sales_change_text = 'Belum ada omzet hari ini maupun kemarin'

    expense_total = filter_selected_cycle(request, OperationalExpense.objects.all()).aggregate(s=Sum('amount'))['s'] or 0

    # Realisasi panen riil diambil langsung dari menu Panen pada siklus terpilih.
    selected_cycle = get_selected_cycle(request)
    harvest_qs = filter_selected_cycle(
        request,
        Harvest.objects.select_related('pond').order_by('-date', '-id'),
    )
    harvest_total_kg = harvest_qs.aggregate(total=Sum('total_kg'))['total'] or Decimal('0')
    harvest_total_ton = harvest_total_kg / Decimal('1000')
    harvest_count = harvest_qs.count()
    latest_harvests = list(harvest_qs[:8])

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
    for harvest in harvest_qs.order_by('date', 'id'):
        harvests_by_pond.setdefault(harvest.pond_id, []).append(harvest)

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
    production_total_kg = 0.0
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

        # Hanya panen setelah sampling yang mengurangi snapshot biomassa terbaru.
        partial_harvests = [
            h for h in harvests_by_pond.get(pond.id, [])
            if h.date >= record.date and not _is_total_harvest_type(h.harvest_type)
        ]
        partial_kg = sum((Decimal(str(h.total_kg or 0)) for h in partial_harvests), Decimal('0'))
        remaining_biomass = max(Decimal('0'), sampling_biomass - partial_kg)
        remaining_population = population_fr
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

        if pond.id in completed_pond_ids:
            pond.dashboard_size30_status = 'Kolam sudah selesai panen'
            pond.dashboard_doc120_status = 'Tidak dihitung: panen total/selesai'
            continue

        # Biomassa produksi hanya menunjukkan yang masih berada di kolam.
        production_items.append({
            'pond': pond,
            'biomass_kg': float(remaining_biomass),
            'biomass_ton': float(remaining_biomass / Decimal('1000')),
        })
        production_total_kg += float(remaining_biomass)
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

    production_total_ton = production_total_kg / 1000
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
    context = {
        'ponds': ponds,
        'sales_total': sales_total,
        'yesterday_sales_total': yesterday_sales_total,
        'sales_change_percent': sales_change_percent,
        'sales_change_state': sales_change_state,
        'sales_change_text': sales_change_text,
        'expense_total': expense_total,
        'selected_cycle': selected_cycle,
        'harvest_total_kg': harvest_total_kg,
        'harvest_total_ton': harvest_total_ton,
        'harvest_count': harvest_count,
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
        'production_total_kg': production_total_kg,
        'production_total_ton': production_total_ton,
        'production_gradient': production_gradient,
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
