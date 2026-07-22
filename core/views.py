from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from ponds.models import Pond
from operations.models import DailyParameter, SamplingRecord
from sales.models import Sale
from finance.models import OperationalExpense
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import math
from chat_ai.services import ollama_health
from cultivation.utils import filter_selected_cycle
from core.weather_service import get_farm_weather

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

    # Produksi aktual berasal dari Biomassa FR pada satu batch/tanggal sampling
    # terbaru di siklus aktif. Satu record terbaru dipakai untuk setiap kolam.
    sampling_qs = filter_selected_cycle(
        request,
        SamplingRecord.objects.select_related('pond').order_by('-date', '-created_at', '-id'),
    )
    latest_sampling_date = sampling_qs.values_list('date', flat=True).first()
    production_items = []
    production_total_kg = 0.0
    if latest_sampling_date:
        seen_ponds = set()
        for record in sampling_qs.filter(date=latest_sampling_date).order_by('pond__name', '-created_at', '-id'):
            if record.pond_id in seen_ponds:
                continue
            seen_ponds.add(record.pond_id)
            biomass_kg = float(record.biomass_kg or 0)
            if biomass_kg < 0:
                biomass_kg = 0
            production_items.append({
                'pond': record.pond,
                'biomass_kg': biomass_kg,
                'biomass_ton': biomass_kg / 1000,
            })
            production_total_kg += biomass_kg

    production_total_ton = production_total_kg / 1000

    # Padat tebar aktual untuk Ringkasan Kolam.
    # Sumber utama adalah nilai Tebar pada satu batch/tanggal sampling terbaru
    # yang sama dengan grafik biomassa. Jangan memakai nilai default/hardcode.
    latest_sampling_by_pond = {
        item['pond'].id: item for item in production_items
    }
    # production_items hanya menyimpan biomassa; ambil kembali record sampling
    # terpilih agar stocking_count dapat digunakan untuk menghitung ekor/m2.
    selected_sampling_records = {}
    if latest_sampling_date:
        for record in sampling_qs.filter(date=latest_sampling_date).order_by('pond__name', '-created_at', '-id'):
            if record.pond_id not in selected_sampling_records:
                selected_sampling_records[record.pond_id] = record

    # Target panen size 30 = ABW 33,33 gram/ekor. Estimasi memakai
    # ABW dan ADG Actual dari sampling terakhir pada batch aktif.
    target_size_30 = Decimal('30')
    target_abw_30 = Decimal('1000') / target_size_30

    # Estimasi produksi pada DOC 120. Proyeksi memakai ABW dan ADG Actual
    # dari batch sampling terakhir serta populasi FR saat sampling. Asumsi: tidak
    # ada panen parsial dan populasi tetap sampai DOC 120.
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

        if record:
            current_abw = Decimal(str(record.abw_g or 0))
            adg_actual = Decimal(str(record.adg_weekly or 0))
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
            population_fr = int(record.population or 0)
            remaining_doc_days = max(doc120_target - current_doc, 0)
            pond.dashboard_doc120_days = remaining_doc_days
            if current_abw > 0 and adg_actual > 0 and population_fr > 0:
                projected_abw = current_abw + (adg_actual * Decimal(remaining_doc_days))
                projected_size = (Decimal('1000') / projected_abw) if projected_abw > 0 else Decimal('0')
                projected_biomass = (Decimal(population_fr) * projected_abw / Decimal('1000'))
                pond.dashboard_doc120_abw = projected_abw.quantize(Decimal('0.01'))
                pond.dashboard_doc120_size = projected_size.quantize(Decimal('0.01'))
                pond.dashboard_doc120_biomass_kg = projected_biomass.quantize(Decimal('0.01'))
                pond.dashboard_doc120_biomass_ton = (projected_biomass / Decimal('1000')).quantize(Decimal('0.01'))
                pond.dashboard_doc120_status = 'Proyeksi berdasarkan ADG aktual dan populasi FR'
                doc120_total_kg += projected_biomass
            elif population_fr <= 0:
                pond.dashboard_doc120_status = 'Populasi FR belum tersedia'
            elif adg_actual <= 0:
                pond.dashboard_doc120_status = 'ADG aktual belum tersedia'

    doc120_total_ton = doc120_total_kg / Decimal('1000')
    doc120_normal_ton = doc120_total_ton * Decimal('0.95')
    doc120_conservative_ton = doc120_total_ton * Decimal('0.90')

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
