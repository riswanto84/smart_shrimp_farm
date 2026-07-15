import math
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.rbac import permission_required
from ponds.models import Pond
from .models import (
    DailyParameter, Treatment, FeedLog, Harvest,
    DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord, Stocking,
)
from chat_ai.services import ask_ollama, ollama_health
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf, angka
from core.pagination import paginate_queryset
from cultivation.utils import get_selected_cycle, filter_selected_cycle


def _selected_pond(request):
    pond = request.GET.get('pond') or ''
    return pond


def _apply_common_filters(request, qs, date_field='date'):
    date_from, date_to = get_date_range(request)
    qs = filter_by_date_range(qs, date_field, date_from, date_to)
    qs = filter_selected_cycle(request, qs)
    pond = _selected_pond(request)
    if pond:
        qs = qs.filter(pond_id=pond)
    return qs, date_from, date_to, pond


def _pct(value, total):
    try:
        if not total:
            return 0
        return round(float(value or 0) / float(total) * 100, 1)
    except Exception:
        return 0


def _float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _post_decimal(value, default='0'):
    if value in (None, ''):
        return default
    return str(value).replace('.', '').replace(',', '.') if ',' in str(value) else str(value)


def _parse_decimal_input(value, label, errors, required=False, min_value=None):
    """Validasi angka desimal dari form.
    Menerima titik atau koma sebagai pemisah desimal, tetapi menolak huruf/simbol.
    Return Decimal/None dan mengisi dict errors agar user mendapat notifikasi.
    """
    raw = (value or '').strip()
    if not raw:
        if required:
            errors[label] = f'{label} wajib diisi.'
        return None
    normalized = raw.replace(',', '.')
    # Field parameter harian harus angka sederhana, bukan format ribuan bercampur.
    if normalized.count('.') > 1 or any(ch not in '0123456789.-' for ch in normalized):
        errors[label] = f'{label} harus berupa angka. Contoh: 90, 90.5, atau 7.6.'
        return None
    try:
        val = Decimal(normalized)
    except (InvalidOperation, ValueError):
        errors[label] = f'{label} harus berupa angka desimal yang valid.'
        return None
    if min_value is not None and val < Decimal(str(min_value)):
        errors[label] = f'{label} tidak boleh kurang dari {min_value}.'
        return None
    return val


def _parse_int_input(value, label, errors, required=False, min_value=None):
    raw = (value or '').strip()
    if not raw:
        if required:
            errors[label] = f'{label} wajib diisi.'
        return 0
    if not raw.isdigit():
        errors[label] = f'{label} harus berupa bilangan bulat tanpa desimal.'
        return 0
    val = int(raw)
    if min_value is not None and val < min_value:
        errors[label] = f'{label} tidak boleh kurang dari {min_value}.'
    return val


def _parameter_payload(request):
    errors = {}
    data = {
        'pond_id': request.POST.get('pond'),
        'date': request.POST.get('date'),
        'doc': _parse_int_input(request.POST.get('doc'), 'DOC', errors, min_value=0),
        'feed_code': request.POST.get('feed_code', '').strip(),
        'water_in_cm': _parse_decimal_input(request.POST.get('water_in_cm'), 'Air Masuk', errors, min_value=0),
        'weather': request.POST.get('weather', '').strip(),
        'water_level_morning_cm': _parse_decimal_input(request.POST.get('water_level_morning_cm'), 'Tinggi Air Pagi', errors, min_value=0),
        'water_level_evening_cm': _parse_decimal_input(request.POST.get('water_level_evening_cm'), 'Tinggi Air Sore', errors, min_value=0),
        'temperature': _parse_decimal_input(request.POST.get('temperature'), 'Suhu Air', errors, min_value=0),
        'ph_morning': _parse_decimal_input(request.POST.get('ph_morning'), 'pH Pagi', errors, min_value=0),
        'ph_evening': _parse_decimal_input(request.POST.get('ph_evening'), 'pH Sore', errors, min_value=0),
        'do_morning': _parse_decimal_input(request.POST.get('do_morning'), 'DO Pagi', errors, min_value=0),
        'do_night': _parse_decimal_input(request.POST.get('do_night'), 'DO Malam', errors, min_value=0),
        'salinity': _parse_decimal_input(request.POST.get('salinity'), 'Salinitas', errors, min_value=0),
        'alkalinity': _parse_decimal_input(request.POST.get('alkalinity'), 'Alkalinitas', errors, min_value=0),
        'transparency_morning': _parse_decimal_input(request.POST.get('transparency_morning'), 'Kecerahan Pagi', errors, min_value=0),
        'transparency_evening': _parse_decimal_input(request.POST.get('transparency_evening'), 'Kecerahan Sore', errors, min_value=0),
        'feed_kg': _parse_decimal_input(request.POST.get('feed_kg') or '0', 'Pakan Harian', errors, min_value=0) or Decimal('0'),
        'mortality': _parse_int_input(request.POST.get('mortality') or '0', 'Mortalitas', errors, min_value=0),
        'water_color_morning': request.POST.get('water_color_morning', '').strip(),
        'water_color_evening': request.POST.get('water_color_evening', '').strip(),
        'notes': request.POST.get('notes', '').strip(),
    }
    if not data['pond_id']:
        errors['Kolam'] = 'Kolam wajib dipilih.'
    if not data['date']:
        errors['Tanggal'] = 'Tanggal wajib diisi.'
    valid_weather = [choice[0] for choice in DailyParameter.WEATHER_CHOICES]
    if data.get('weather') and data['weather'] not in valid_weather:
        errors['Cuaca'] = 'Cuaca harus dipilih dari daftar yang tersedia.'
    if data.get('feed_code') and len(data['feed_code']) > 80:
        errors['Kode Pakan'] = 'Kode pakan maksimal 80 karakter.'
    # Simpan juga ke field lama agar dashboard lama tetap kompatibel.
    data['water_level_cm'] = data.get('water_level_morning_cm') or data.get('water_level_evening_cm')
    data['transparency'] = data.get('transparency_morning') or data.get('transparency_evening')
    data['water_color'] = data.get('water_color_morning') or data.get('water_color_evening') or ''
    return data, errors


def _parameter_ai_prompt(obj):
    return (
        f"Anda asisten tambak udang vaname. Analisa parameter kolam {obj.pond.name}: "
        f"DOC {obj.doc}, kode pakan {obj.feed_code or '-'}, pakan harian {obj.feed_kg} kg, air masuk {obj.water_in_cm} cm, cuaca {obj.weather or '-'}, "
        f"tinggi air pagi {obj.water_level_morning_cm} cm, tinggi air sore {obj.water_level_evening_cm} cm, "
        f"suhu {obj.temperature}, pH pagi {obj.ph_morning}, pH sore {obj.ph_evening}, DO pagi {obj.do_morning}, "
        f"DO malam {obj.do_night}, salinitas {obj.salinity}, alkalinitas {obj.alkalinity}, "
        f"kecerahan pagi {obj.transparency_morning} cm, kecerahan sore {obj.transparency_evening} cm, "
        f"warna air pagi {obj.water_color_morning}, warna air sore {obj.water_color_evening}. "
        f"Berikan status, risiko, dan rekomendasi singkat."
    )




def _anco_payload(request):
    errors = {}
    valid_statuses = [choice[0] for choice in AncoCheck.STATUS_CHOICES]
    data = {
        'pond_id': request.POST.get('pond'),
        'date': request.POST.get('date'),
        'doc': _parse_int_input(request.POST.get('doc'), 'DOC', errors, min_value=0),
        'feed_code': request.POST.get('feed_code', '').strip(),
        'daily_feed_kg': _parse_decimal_input(request.POST.get('daily_feed_kg') or '0', 'P/H - Pakan Harian', errors, min_value=0) or Decimal('0'),
        'water_in_cm': _parse_decimal_input(request.POST.get('water_in_cm'), 'Air Masuk', errors, min_value=0),
        'weather': request.POST.get('weather', '').strip(),
        'treatment': request.POST.get('treatment', '').strip(),
        'anco1_morning': request.POST.get('anco1_morning', '-'),
        'anco2_morning': request.POST.get('anco2_morning', '-'),
        'anco1_noon': request.POST.get('anco1_noon', '-'),
        'anco2_noon': request.POST.get('anco2_noon', '-'),
        'anco1_evening': request.POST.get('anco1_evening', '-'),
        'anco2_evening': request.POST.get('anco2_evening', '-'),
        'notes': request.POST.get('notes', '').strip(),
    }
    if not data['pond_id']:
        errors['Kolam'] = 'Kolam wajib dipilih.'
    if not data['date']:
        errors['Tanggal'] = 'Tanggal wajib diisi.'
    if data.get('feed_code') and len(data['feed_code']) > 80:
        errors['Kode Pakan'] = 'Kode pakan maksimal 80 karakter.'
    if data.get('weather') and data['weather'] not in [choice[0] for choice in DailyPondRecord.WEATHER_CHOICES]:
        errors['Cuaca'] = 'Cuaca harus dipilih dari daftar yang tersedia.'
    for key in ['anco1_morning','anco2_morning','anco1_noon','anco2_noon','anco1_evening','anco2_evening']:
        if data[key] not in valid_statuses:
            errors[key] = 'Status anco harus H, S, SS, atau Tidak Dicek.'
    return data, errors


def _daily_record_payload(request):
    errors = {}
    data = {
        'pond_id': request.POST.get('pond'),
        'date': request.POST.get('date'),
        'doc': _parse_int_input(request.POST.get('doc') or '0', 'DOC', errors, min_value=0),
        'feed_code': request.POST.get('feed_code', '').strip(),
        'daily_feed_kg': _parse_decimal_input(request.POST.get('daily_feed_kg') or '0', 'Pakan Harian', errors, min_value=0) or Decimal('0'),
        'water_in_cm': _parse_decimal_input(request.POST.get('water_in_cm'), 'Air Masuk', errors, min_value=0),
        'weather': request.POST.get('weather', '').strip(),
        'treatment': request.POST.get('treatment', '').strip(),
        'notes': request.POST.get('notes', '').strip(),
    }
    if not data['pond_id']:
        errors['Kolam'] = 'Kolam wajib dipilih.'
    if not data['date']:
        errors['Tanggal'] = 'Tanggal wajib diisi.'
    if data.get('feed_code') and len(data['feed_code']) > 80:
        errors['Kode Pakan'] = 'Kode pakan maksimal 80 karakter.'
    if data.get('weather') and data['weather'] not in [choice[0] for choice in DailyPondRecord.WEATHER_CHOICES]:
        errors['Cuaca'] = 'Cuaca harus dipilih dari daftar yang tersedia.'
    return data, errors


def _siphon_payload(request):
    errors = {}
    data = {
        'pond_id': request.POST.get('pond'),
        'date': request.POST.get('date'),
        'doc': _parse_int_input(request.POST.get('doc') or '0', 'DOC', errors, min_value=0),
        'dead_count': _parse_int_input(request.POST.get('dead_count') or '0', 'Udang Mati', errors, min_value=0),
        'live_count': _parse_int_input(request.POST.get('live_count') or '0', 'Udang Hidup Ikut Tersiphon', errors, min_value=0),
        'notes': request.POST.get('notes', '').strip(),
    }
    if not data['pond_id']:
        errors['Kolam'] = 'Kolam wajib dipilih.'
    if not data['date']:
        errors['Tanggal'] = 'Tanggal wajib diisi.'
    return data, errors


def _harvest_payload(request):
    errors = {}
    data = {
        'pond_id': request.POST.get('pond'),
        'date': request.POST.get('date'),
        'harvest_type': request.POST.get('harvest_type', 'Parsial').strip() or 'Parsial',
        'size_text': request.POST.get('size_text', '').strip(),
        'total_kg': _parse_decimal_input(request.POST.get('total_kg'), 'Total Kg', errors, required=True, min_value=0),
        'notes': request.POST.get('notes', '').strip(),
    }
    if not data['pond_id']:
        errors['Kolam'] = 'Kolam wajib dipilih.'
    if not data['date']:
        errors['Tanggal'] = 'Tanggal wajib diisi.'
    if data['harvest_type'] not in ['Parsial', 'Total']:
        errors['Jenis Panen'] = 'Jenis panen harus Parsial atau Total.'
    if not data['size_text']:
        errors['Size Udang'] = 'Size udang wajib diisi.'
    if data['size_text'] and len(data['size_text']) > 50:
        errors['Size Udang'] = 'Size udang maksimal 50 karakter.'
    if data['total_kg'] is None:
        data['total_kg'] = Decimal('0')
    return data, errors


def _parameter_risk(obj):
    risk = []
    try:
        if obj.do_morning is not None and obj.do_morning < Decimal('4'):
            risk.append('DO pagi rendah')
        if obj.do_night is not None and obj.do_night < Decimal('4'):
            risk.append('DO malam rendah')
        if obj.ph_morning is not None and (obj.ph_morning < Decimal('7.2') or obj.ph_morning > Decimal('8.5')):
            risk.append('pH pagi di luar ideal')
        if obj.ph_evening is not None and (obj.ph_evening < Decimal('7.2') or obj.ph_evening > Decimal('8.8')):
            risk.append('pH sore di luar ideal')
        if obj.salinity is not None and (obj.salinity < Decimal('10') or obj.salinity > Decimal('35')):
            risk.append('Salinitas perlu dicek')
        if obj.mortality and obj.mortality > 20:
            risk.append('Mortalitas meningkat')
    except Exception:
        pass
    if len(risk) >= 2:
        return 'Waspada', ', '.join(risk)
    if len(risk) == 1:
        return 'Perhatian', risk[0]
    return 'Baik', 'Parameter utama dalam rentang aman.'

def _sampling_pond_meta():
    today = timezone.localdate()
    meta = {}
    for pond in Pond.objects.all():
        latest_sample = SamplingRecord.objects.filter(pond=pond).order_by('-date').first()
        stocking = Stocking.objects.filter(pond=pond).order_by('-date').first()
        latest_daily = DailyPondRecord.objects.filter(pond=pond).order_by('-date').first()
        feed_total = DailyPondRecord.objects.filter(pond=pond, date__lte=today).aggregate(s=Sum('daily_feed_kg'))['s'] or Decimal('0')
        meta[str(pond.id)] = {
            'last_abw': _float(latest_sample.abw_g if latest_sample else 0),
            'last_date': latest_sample.date.isoformat() if latest_sample else '',
            'stocking_count': int(stocking.seed_count) if stocking else 0,
            'daily_feed_kg': _float(latest_daily.daily_feed_kg if latest_daily else 0),
            'cumulative_feed_kg': _float(feed_total),
            'latest_doc': int(latest_daily.doc) if latest_daily else int(latest_sample.doc) if latest_sample else 0,
        }
    return meta


def _sampling_payload(request):
    errors = {}
    data = {
        'pond_id': request.POST.get('pond'),
        'date': request.POST.get('date'),
        'doc': _parse_int_input(request.POST.get('doc') or '0', 'DOC', errors, min_value=0),
        'sample_weight_g': _parse_decimal_input(request.POST.get('sample_weight_g') or '0', 'Berat SHRIMP', errors, min_value=0) or Decimal('0'),
        'sample_count': _parse_int_input(request.POST.get('sample_count') or '0', 'Jumlah SHRIMP', errors, min_value=0),
        'adg_weekly_target': _parse_decimal_input(request.POST.get('adg_weekly_target') or '0', 'ADG Weekly Target', errors, min_value=0) or Decimal('0'),
        'cumulative_feed_kg': _parse_decimal_input(request.POST.get('cumulative_feed_kg') or '0', 'Pakan Kumulatif', errors, min_value=0) or Decimal('0'),
        'stocking_count': _parse_int_input(request.POST.get('stocking_count') or '0', 'Tebar', errors, min_value=0),
        'daily_feed_kg': _parse_decimal_input(request.POST.get('daily_feed_kg') or '0', 'F/D - Pakan Harian', errors, min_value=0) or Decimal('0'),
        'fr_percent': _parse_decimal_input(request.POST.get('fr_percent') or '0', 'FR (%)', errors, min_value=0) or Decimal('0'),
        'population_index': _parse_int_input(request.POST.get('population_index') or '0', 'Populasi Index', errors, min_value=0),
        'index_score': _parse_decimal_input(request.POST.get('index_score') or '0', 'Index', errors, min_value=0) or Decimal('0'),
        'harvest_estimation': request.POST.get('harvest_estimation', '').strip(),
        'notes': request.POST.get('notes', '').strip(),
    }
    if not data['pond_id']:
        errors['Kolam'] = 'Kolam wajib dipilih.'
    if not data['date']:
        errors['Tanggal'] = 'Tanggal sampling wajib diisi.'
    return data, errors


@login_required
@permission_required('operations.production_dashboard')
def production_dashboard(request):
    """Dashboard produksi dengan data aktual berdasarkan siklus terpilih.

    Sumber data dibuat berlapis agar dashboard tidak tampak kosong ketika
    modul lama belum diisi, tetapi data ekuivalen sudah tersedia di sampling
    atau cek anco. Record lama dengan ``cycle=NULL`` tetap dibaca melalui
    ``filter_selected_cycle`` selama masa transisi.
    """
    ponds = Pond.objects.all().order_by('name')
    today = timezone.localdate()
    selected_cycle = get_selected_cycle(request)

    def cycle_qs(qs):
        return filter_selected_cycle(request, qs)

    def latest_per_pond(qs):
        result = {}
        for obj in qs.select_related('pond').order_by('pond_id', '-date', '-id'):
            if obj.pond_id not in result:
                result[obj.pond_id] = obj
        return result

    # Sampling terbaru per kolam menjadi dasar KPI, bukan rata-rata seluruh histori.
    sampling_qs = cycle_qs(SamplingRecord.objects.all())
    sampling_map = latest_per_pond(sampling_qs)
    latest_samples = list(sampling_map.values())
    avg_abw = (
        sum((_float(x.abw_g) for x in latest_samples), 0.0) / len(latest_samples)
        if latest_samples else 0
    )
    # Gunakan nilai tersimpan bila tersedia. Untuk data lama/import yang belum
    # menyimpan hasil turunan, hitung ulang FCR dan biomassa dari data dasar.
    def effective_sampling_metrics(sample):
        abw = _float(getattr(sample, 'abw_g', 0))

        biomass = _float(getattr(sample, 'biomass_kg', 0))
        if biomass <= 0:
            biomass = _float(getattr(sample, 'biomass_index_kg', 0))

        population = _float(getattr(sample, 'population', 0))
        if population <= 0:
            population = _float(getattr(sample, 'population_index', 0))

        # Fallback terakhir: estimasi populasi hidup dari tebar dan SR.
        if population <= 0:
            stocking = _float(getattr(sample, 'stocking_count', 0))
            sr = _float(getattr(sample, 'estimated_sr', 0)) or _float(getattr(sample, 'sr_index_percent', 0))
            if stocking > 0 and sr > 0:
                population = stocking * sr / 100.0

        if biomass <= 0 and population > 0 and abw > 0:
            biomass = population * abw / 1000.0

        fcr = _float(getattr(sample, 'fcr', 0))
        cumulative_feed = _float(getattr(sample, 'cumulative_feed_kg', 0))
        if fcr <= 0 and cumulative_feed > 0 and biomass > 0:
            fcr = cumulative_feed / biomass

        # Atribut runtime untuk digunakan langsung di template dashboard.
        sample.dashboard_biomass_kg = biomass
        sample.dashboard_fcr = fcr
        return biomass, fcr

    effective_metrics = [effective_sampling_metrics(x) for x in latest_samples]
    fcr_values = [fcr for _, fcr in effective_metrics if fcr > 0]
    avg_fcr = sum(fcr_values, 0.0) / len(fcr_values) if fcr_values else 0
    estimated_biomass = sum((biomass for biomass, _ in effective_metrics), 0.0)

    # Populasi tebar pada Dashboard Produksi berasal langsung dari kapasitas
    # tebar di Master Kolam. Dengan demikian angka pada dashboard selalu sama
    # dengan total kolom `capacity_seed` yang dilihat pengguna di menu Master
    # Kolam, dan tidak berubah hanya karena data sampling/stocking belum diisi.
    #
    # Catatan: ini adalah kapasitas/populasi tebar yang ditetapkan pada master,
    # bukan estimasi populasi hidup dari sampling.
    active_stocking = ponds.aggregate(s=Sum('capacity_seed'))['s'] or 0
    stocking_source = 'Master Kolam'

    # Pakan memakai satu sumber prioritas agar tidak terjadi hitung ganda.
    feed_sources = [
        ('Cek Anco', AncoCheck, 'daily_feed_kg'),
        ('Data Harian', DailyPondRecord, 'daily_feed_kg'),
        ('Log Pakan', FeedLog, 'quantity_kg'),
        ('Parameter Harian', DailyParameter, 'feed_kg'),
        ('Sampling', SamplingRecord, 'daily_feed_kg'),
    ]
    feed_value = Decimal('0')
    feed_date = None
    feed_source = 'Belum ada data'
    feed_is_today = False

    # Coba data hari ini terlebih dahulu sesuai urutan prioritas.
    for source_name, model, field_name in feed_sources:
        qs = cycle_qs(model.objects.filter(date=today))
        value = qs.aggregate(s=Sum(field_name))['s'] or Decimal('0')
        if value:
            feed_value = value
            feed_date = today
            feed_source = source_name
            feed_is_today = True
            break

    # Bila hari ini belum diinput, tampilkan pakan pada tanggal terbaru yang ada.
    if not feed_value:
        latest_candidates = []
        for source_name, model, field_name in feed_sources:
            qs = cycle_qs(model.objects.all())
            latest_obj = qs.order_by('-date', '-id').first()
            if latest_obj:
                latest_candidates.append((latest_obj.date, source_name, model, field_name))
        if latest_candidates:
            feed_date, feed_source, model, field_name = max(latest_candidates, key=lambda x: x[0])
            feed_value = (
                cycle_qs(model.objects.filter(date=feed_date))
                .aggregate(s=Sum(field_name))['s'] or Decimal('0')
            )

    # Alert dan siphon juga wajib mengikuti siklus terpilih.
    siphon_qs = cycle_qs(SiphonRecord.objects.all())
    anco_qs = cycle_qs(AncoCheck.objects.all())
    dead_7d = siphon_qs.filter(date__gte=today - timedelta(days=7)).aggregate(
        s=Sum('dead_count')
    )['s'] or 0
    anco_alerts = anco_qs.filter(
        date__gte=today - timedelta(days=3),
        appetite_status__in=['Nafsu makan turun', 'Ada sisa pakan'],
    ).count()

    siphon_map = latest_per_pond(siphon_qs)
    anco_map = latest_per_pond(anco_qs)
    daily_map = latest_per_pond(cycle_qs(DailyPondRecord.objects.all()))
    parameter_map = latest_per_pond(cycle_qs(DailyParameter.objects.all()))
    feedlog_map = latest_per_pond(cycle_qs(FeedLog.objects.all()))

    pond_cards = []
    for pond in ponds:
        sample = sampling_map.get(pond.id)
        daily = daily_map.get(pond.id)
        parameter = parameter_map.get(pond.id)
        anco = anco_map.get(pond.id)
        feedlog = feedlog_map.get(pond.id)

        # Pilih catatan pakan terbaru per kolam dari seluruh sumber.
        feed_options = []
        if anco and _float(anco.daily_feed_kg) > 0:
            feed_options.append((anco.date, anco.daily_feed_kg, 'Cek Anco'))
        if daily and _float(daily.daily_feed_kg) > 0:
            feed_options.append((daily.date, daily.daily_feed_kg, 'Data Harian'))
        if feedlog and _float(feedlog.quantity_kg) > 0:
            feed_options.append((feedlog.date, feedlog.quantity_kg, 'Log Pakan'))
        if parameter and _float(parameter.feed_kg) > 0:
            feed_options.append((parameter.date, parameter.feed_kg, 'Parameter'))
        if sample and _float(sample.daily_feed_kg) > 0:
            feed_options.append((sample.date, sample.daily_feed_kg, 'Sampling'))
        latest_feed = max(feed_options, key=lambda x: x[0]) if feed_options else None

        doc_candidates = [
            (obj.date, obj.doc) for obj in (anco, daily, parameter, sample)
            if obj is not None and getattr(obj, 'doc', None) is not None
        ]
        latest_doc = max(doc_candidates, key=lambda x: x[0])[1] if doc_candidates else None

        pond_cards.append({
            'pond': pond,
            'sample': sample,
            'siphon': siphon_map.get(pond.id),
            'anco': anco,
            'daily': daily,
            'parameter': parameter,
            'latest_feed': latest_feed,
            'latest_doc': latest_doc,
        })

    # ---------------------------------------------------------------
    # Grafik perkembangan produksi berbasis seluruh histori sampling.
    # Setiap titik merupakan total satu batch/tanggal sampling, dengan satu
    # record terbaru per kolam agar duplikat impor tidak menggandakan nilai.
    # ---------------------------------------------------------------
    history_by_date = {}
    history_seen = set()
    for sample in sampling_qs.select_related('pond').order_by('date', 'pond_id', '-id'):
        key = (sample.date, sample.pond_id)
        if key in history_seen:
            continue
        history_seen.add(key)
        biomass, fcr = effective_sampling_metrics(sample)
        bucket = history_by_date.setdefault(sample.date, {
            'date': sample.date,
            'docs': [], 'biomass_kg': 0.0, 'abw': [], 'adg': [],
            'fcr': [], 'sr': [], 'population': 0,
        })
        bucket['docs'].append(int(sample.doc or 0))
        bucket['biomass_kg'] += max(biomass, 0.0)
        if _float(sample.abw_g) > 0:
            bucket['abw'].append(_float(sample.abw_g))
        if _float(sample.adg_weekly) > 0:
            bucket['adg'].append(_float(sample.adg_weekly))
        if fcr > 0:
            bucket['fcr'].append(fcr)
        sr_value = _float(sample.estimated_sr) or _float(sample.sr_index_percent)
        if sr_value > 0:
            bucket['sr'].append(sr_value)
        bucket['population'] += int(sample.population or sample.population_index or 0)

    biomass_history = []
    for date_value, bucket in sorted(history_by_date.items()):
        avg_doc = round(sum(bucket['docs']) / len(bucket['docs'])) if bucket['docs'] else 0
        biomass_history.append({
            'label': date_value.strftime('%d %b'),
            'date': date_value.isoformat(),
            'doc': avg_doc,
            'biomass_ton': round(bucket['biomass_kg'] / 1000.0, 3),
            'abw': round(sum(bucket['abw']) / len(bucket['abw']), 2) if bucket['abw'] else 0,
            'adg': round(sum(bucket['adg']) / len(bucket['adg']), 3) if bucket['adg'] else 0,
            'fcr': round(sum(bucket['fcr']) / len(bucket['fcr']), 2) if bucket['fcr'] else 0,
            'sr': round(sum(bucket['sr']) / len(bucket['sr']), 2) if bucket['sr'] else 0,
            'population': bucket['population'],
            'size': round(1000.0 / (sum(bucket['abw']) / len(bucket['abw'])), 2) if bucket['abw'] and (sum(bucket['abw']) / len(bucket['abw'])) > 0 else 0,
        })

    # ADG untuk dashboard dihitung ulang dari rumus baku agar nilai impor lama
    # yang keliru (misalnya selisih ABW tanpa dibagi 7) tidak membuat proyeksi
    # biomassa melonjak tidak realistis.
    def safe_actual_adg(sample):
        current_abw = (
            _float(sample.sample_weight_g) / int(sample.sample_count)
            if int(sample.sample_count or 0) > 0 and _float(sample.sample_weight_g) > 0
            else _float(sample.abw_g)
        )
        last_abw = _float(sample.abw_last_g)
        calculated = (current_abw - last_abw) / 7.0 if current_abw > 0 and last_abw > 0 else 0
        stored = _float(sample.adg_weekly)
        adg = calculated if calculated > 0 else stored
        # Rentang pengaman operasional. Nilai di luar rentang ini biasanya
        # menunjukkan data lama/import yang salah, bukan pertumbuhan biologis.
        return adg if 0 < adg <= 0.50 else 0

    avg_adg_values = [safe_actual_adg(x) for x in latest_samples]
    avg_adg_values = [x for x in avg_adg_values if x > 0]
    avg_adg = sum(avg_adg_values) / len(avg_adg_values) if avg_adg_values else 0
    avg_sr_values = [(_float(x.estimated_sr) or _float(x.sr_index_percent)) for x in latest_samples]
    avg_sr_values = [x for x in avg_sr_values if x > 0]
    avg_sr = sum(avg_sr_values) / len(avg_sr_values) if avg_sr_values else 0
    current_population = sum(int(x.population or x.population_index or 0) for x in latest_samples)
    # Size adalah jumlah ekor per kilogram. Gunakan ABW rata-rata sampling
    # terakhir per kolam agar konsisten dengan KPI ABW pada dashboard.
    current_size = (1000.0 / avg_abw) if avg_abw > 0 else 0

    # Target produksi berasal dari Master Siklus Budidaya, bukan hardcode.
    target_harvest_ton = _float(getattr(selected_cycle, 'target_biomass_ton', 25)) or 25.0
    target_doc = int(getattr(selected_cycle, 'target_doc', 120) or 120)
    target_size = _float(getattr(selected_cycle, 'target_size', 30)) or 30.0
    target_sr = _float(getattr(selected_cycle, 'target_sr_percent', 85)) or 85.0
    target_fcr = _float(getattr(selected_cycle, 'target_fcr', 1.20)) or 1.20
    target_adg = _float(getattr(selected_cycle, 'target_adg', 0.25)) or 0.25
    target_population = int(getattr(selected_cycle, 'target_population', 0) or 0)
    estimated_price_per_kg = _float(getattr(selected_cycle, 'estimated_price_per_kg', 0))
    target_cost = _float(getattr(selected_cycle, 'target_cost', 0))
    target_revenue = target_harvest_ton * 1000.0 * estimated_price_per_kg
    target_profit = target_revenue - target_cost
    biomass_progress = min((estimated_biomass / 1000.0) / target_harvest_ton * 100.0, 100.0) if target_harvest_ton else 0

    # Proyeksi biomassa hingga target DOC menggunakan ADG aktual dan populasi FR
    # terbaru per kolam. Garis prediksi sengaja dipisahkan dari data aktual.
    latest_doc = max((int(x.doc or 0) for x in latest_samples), default=0)
    projection_docs = []
    if latest_samples and latest_doc:
        next_doc = latest_doc
        while next_doc < target_doc:
            projection_docs.append(next_doc)
            next_doc += 14
        if target_doc not in projection_docs:
            projection_docs.append(target_doc)

    biomass_projection = []
    target_abw_limit = (1000.0 / target_size) if target_size > 0 else 40.0
    target_abw_grams = target_abw_limit
    valid_adgs = [safe_actual_adg(x) for x in latest_samples]
    valid_adgs = sorted(x for x in valid_adgs if x > 0)
    fallback_adg = (
        valid_adgs[len(valid_adgs) // 2]
        if valid_adgs else min(max(target_adg, 0.0), 0.50)
    )

    for projection_doc in projection_docs:
        total_kg = 0.0
        for sample in latest_samples:
            current_abw = (
                _float(sample.sample_weight_g) / int(sample.sample_count)
                if int(sample.sample_count or 0) > 0 and _float(sample.sample_weight_g) > 0
                else _float(sample.abw_g)
            )
            adg = safe_actual_adg(sample) or fallback_adg
            population = int(sample.population or sample.population_index or 0)
            remaining = max(projection_doc - int(sample.doc or 0), 0)
            if current_abw > 0 and population > 0:
                projected_abw = current_abw + adg * remaining
                # Target size pada siklus menjadi batas panen. Ini mencegah
                # proyeksi terus tumbuh sampai 80 ton akibat ADG lama yang salah.
                projected_abw = min(projected_abw, target_abw_limit)
                total_kg += population * projected_abw / 1000.0
        biomass_projection.append({
            'label': f'DOC {projection_doc}',
            'doc': projection_doc,
            'biomass_ton': round(total_kg / 1000.0, 3),
        })

    # Size proyeksi pada target DOC dihitung dari total biomassa proyeksi
    # dibagi populasi hidup terbaru. Rumus: ABW = biomassa(kg)*1000/populasi,
    # lalu Size = 1000/ABW.
    projected_size_doc = 0
    projected_abw_doc = 0
    if biomass_projection and current_population > 0:
        projected_total_kg = _float(biomass_projection[-1].get('biomass_ton')) * 1000.0
        projected_abw_doc = projected_total_kg * 1000.0 / current_population
        projected_size_doc = 1000.0 / projected_abw_doc if projected_abw_doc > 0 else 0

    # Estimasi tanggal target size siklus diringkas dari estimasi seluruh kolam.
    size30_dates = []
    target_abw = 1000.0 / target_size if target_size > 0 else 0
    for sample in latest_samples:
        abw = _float(sample.abw_g)
        adg = _float(sample.adg_weekly)
        if abw >= target_abw:
            size30_dates.append(sample.date)
        elif abw > 0 and adg > 0:
            days = math.ceil((target_abw - abw) / adg)
            size30_dates.append(sample.date + timedelta(days=max(days, 0)))
    estimated_size30_date = max(size30_dates) if size30_dates else None

    context = {
        'ponds': ponds,
        'selected_cycle': selected_cycle,
        'biomass_history': biomass_history,
        'biomass_projection': biomass_projection,
        'doc120_projection_ton': biomass_projection[-1]['biomass_ton'] if biomass_projection else 0,
        'target_doc': target_doc,
        'target_size': target_size,
        'target_abw_grams': target_abw_grams,
        'target_sr': target_sr,
        'target_fcr': target_fcr,
        'target_adg': target_adg,
        'target_population': target_population,
        'estimated_price_per_kg': estimated_price_per_kg,
        'target_cost': target_cost,
        'target_revenue': target_revenue,
        'target_profit': target_profit,
        'target_harvest_ton': target_harvest_ton,
        'biomass_progress': biomass_progress,
        'avg_adg': avg_adg,
        'avg_sr': avg_sr,
        'current_population': current_population,
        'current_size': current_size,
        'projected_size_doc': projected_size_doc,
        'projected_abw_doc': projected_abw_doc,
        'estimated_size30_date': estimated_size30_date,
        'feed_today': feed_value,
        'feed_date': feed_date,
        'feed_source': feed_source,
        'feed_is_today': feed_is_today,
        'avg_abw': avg_abw,
        'avg_fcr': avg_fcr,
        'estimated_biomass': estimated_biomass,
        'dead_7d': dead_7d,
        'anco_alerts': anco_alerts,
        'active_stocking': active_stocking,
        'stocking_source': stocking_source,
        'latest_samples': latest_samples[:8],
        'pond_cards': pond_cards,
        'ollama_health': ollama_health(),
    }
    return render(request, 'operations/production_dashboard.html', context)


# ---------------------------------------------------------------------
# Existing Parameter Harian module, retained for compatibility.
# ---------------------------------------------------------------------
def _parameter_queryset(request):
    date_from, date_to = get_date_range(request)
    items = DailyParameter.objects.select_related('pond', 'technician').order_by('-date')
    items = filter_by_date_range(items, 'date', date_from, date_to)
    pond = request.GET.get('pond') or ''
    if pond:
        items = items.filter(pond_id=pond)
    return items, date_from, date_to


def _parameter_rows(items):
    rows = []
    for i in items:
        rows.append([
            i.date.strftime('%d/%m/%Y'), i.pond.name, i.doc,
            i.feed_code, i.water_in_cm, i.weather,
            i.water_level_morning_cm or i.water_level_cm, i.water_level_evening_cm or i.water_level_cm,
            i.temperature, i.ph_morning, i.ph_evening, i.do_morning, i.do_night,
            i.salinity, i.alkalinity,
            i.transparency_morning or i.transparency, i.transparency_evening or i.transparency,
            i.feed_kg, i.mortality,
            i.water_color_morning or i.water_color, i.water_color_evening or i.water_color,
            i.technician.username if i.technician else '-', i.ai_recommendation,
        ])
    return rows




@login_required
@permission_required('operations.parameter_dashboard')
def parameter_dashboard(request):
    items, date_from, date_to = _parameter_queryset(request)
    today = timezone.localdate()
    latest_qs = DailyParameter.objects.select_related('pond').order_by('pond_id', '-date', '-id')
    latest_map = {}
    for obj in latest_qs:
        if obj.pond_id not in latest_map:
            latest_map[obj.pond_id] = obj
    latest_items = list(latest_map.values())
    ponds = Pond.objects.all().order_by('name')
    input_today = DailyParameter.objects.filter(date=today).values('pond_id').distinct().count()
    total_ponds = ponds.count()
    not_input_count = max(total_ponds - input_today, 0)
    avg = items.aggregate(
        ph_pagi=Avg('ph_morning'), ph_sore=Avg('ph_evening'),
        do_pagi=Avg('do_morning'), do_malam=Avg('do_night'),
        salinity=Avg('salinity'), transparency=Avg('transparency_morning'),
        feed=Sum('feed_kg'), water_in=Sum('water_in_cm'), mortality=Sum('mortality')
    )
    weather_rows = items.values('weather').annotate(total=Count('id')).order_by('-total')[:5]
    risk_cards = []
    for obj in latest_items[:12]:
        status, reason = _parameter_risk(obj)
        risk_cards.append({'obj': obj, 'status': status, 'reason': reason})
    context = {
        'items': items[:20], 'ponds': ponds, 'date_from': date_from, 'date_to': date_to,
        'input_today': input_today, 'total_ponds': total_ponds, 'not_input_count': not_input_count,
        'avg': avg, 'weather_rows': weather_rows, 'risk_cards': risk_cards,
    }
    return render(request, 'operations/parameter_dashboard.html', context)


@login_required
@permission_required('operations.parameters')
def parameters(request):
    items, date_from, date_to = _parameter_queryset(request)
    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'operations/parameters.html', {'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(), 'cycle_is_locked': bool(get_selected_cycle(request) and not get_selected_cycle(request).is_open)})


@login_required
@permission_required('operations.parameters')
def export_parameters_excel(request):
    items, date_from, date_to = _parameter_queryset(request)
    return export_excel(
        'laporan_parameter_harian', 'Laporan Parameter Harian', f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kolam', 'DOC', 'Kode Pakan', 'Air Masuk Cm', 'Cuaca', 'Tinggi Air Pagi', 'Tinggi Air Sore', 'Suhu', 'pH Pagi', 'pH Sore', 'DO Pagi', 'DO Malam', 'Salinitas', 'Alkalinitas', 'Kecerahan Pagi', 'Kecerahan Sore', 'Pakan Kg', 'Kematian', 'Warna Air Pagi', 'Warna Air Sore', 'Teknisi', 'Rekomendasi AI'],
        _parameter_rows(items),
    )


@login_required
@permission_required('operations.parameters')
def export_parameters_pdf(request):
    items, date_from, date_to = _parameter_queryset(request)
    rows = _parameter_rows(items)
    short_rows = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[10], r[12], r[13], r[15], r[16], r[17], r[21], (r[22] or '')[:80]] for r in rows]
    return export_pdf(
        'laporan_parameter_harian', 'Laporan Parameter Harian', f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kolam', 'DOC', 'Kode', 'Air Masuk', 'Cuaca', 'Tinggi Pagi', 'Tinggi Sore', 'pH Sore', 'DO Malam', 'Salinitas', 'Kecerahan Pagi', 'Kecerahan Sore', 'Pakan', 'Teknisi', 'AI'], short_rows,
    )


@login_required
@permission_required('operations.parameters')
def add_parameter(request):
    ponds = Pond.objects.all()
    if request.method == 'POST':
        payload, errors = _parameter_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/parameter_form.html', {
                'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'obj': payload, 'errors': errors, 'mode': 'add'
            })
        obj = DailyParameter.objects.create(
            cycle=get_selected_cycle(request, required=True),
            pond_id=payload['pond_id'], technician=request.user, date=payload['date'],
            doc=payload['doc'], feed_code=payload['feed_code'], water_in_cm=payload['water_in_cm'], weather=payload['weather'],
            water_level_cm=payload['water_level_cm'],
            water_level_morning_cm=payload['water_level_morning_cm'],
            water_level_evening_cm=payload['water_level_evening_cm'],
            temperature=payload['temperature'], ph_morning=payload['ph_morning'],
            ph_evening=payload['ph_evening'], do_morning=payload['do_morning'],
            do_night=payload['do_night'], salinity=payload['salinity'],
            alkalinity=payload['alkalinity'], transparency=payload['transparency'],
            transparency_morning=payload['transparency_morning'],
            transparency_evening=payload['transparency_evening'],
            feed_kg=payload['feed_kg'], mortality=payload['mortality'],
            water_color=payload['water_color'],
            water_color_morning=payload['water_color_morning'],
            water_color_evening=payload['water_color_evening'],
            notes=payload['notes']
        )
        if 'analyse' in request.POST:
            obj.ai_recommendation = ask_ollama(_parameter_ai_prompt(obj)); obj.save()
        messages.success(request, 'Parameter harian berhasil disimpan.')
        return redirect('operations:parameters')
    return render(request, 'operations/parameter_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'mode': 'add'})


# ---------------------------------------------------------------------
# Operational Core Modules requested for Smart Shrimp Farm.
# ---------------------------------------------------------------------
def _daily_rows(items):
    return [[i.date.strftime('%d/%m/%Y'), i.pond.name, i.doc, i.feed_code, i.daily_feed_kg, i.water_in_cm or '-', i.weather, i.treatment[:80], i.technician.username if i.technician else '-'] for i in items]


@login_required
@permission_required('operations.daily_records')
def daily_records(request):
    items = DailyPondRecord.objects.select_related('pond', 'technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    total_feed = items.aggregate(s=Sum('daily_feed_kg'))['s'] or 0
    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'operations/daily_records.html', {'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(), 'total_feed': total_feed})


@login_required
@permission_required('operations.daily_records')
def add_daily_record(request):
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _daily_record_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/daily_record_form.html', {
                'ponds': ponds, 'weather_choices': DailyPondRecord.WEATHER_CHOICES, 'obj': payload, 'errors': errors
            })
        DailyPondRecord.objects.update_or_create(
            cycle=get_selected_cycle(request, required=True), pond_id=payload['pond_id'], date=payload['date'],
            defaults={
                'technician': request.user,
                'doc': payload['doc'],
                'feed_code': payload['feed_code'],
                'daily_feed_kg': payload['daily_feed_kg'],
                'water_in_cm': payload['water_in_cm'],
                'weather': payload['weather'],
                'treatment': payload['treatment'],
                'notes': payload['notes'],
            }
        )
        messages.success(request, 'Data harian kolam berhasil disimpan.')
        return redirect('operations:daily_records')
    return render(request, 'operations/daily_record_form.html', {'ponds': ponds, 'weather_choices': DailyPondRecord.WEATHER_CHOICES})


@login_required
@permission_required('operations.daily_records')
def export_daily_records_excel(request):
    items = DailyPondRecord.objects.select_related('pond', 'technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    return export_excel('laporan_data_harian_kolam', 'Laporan Data Harian Kolam', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal','Kolam','DOC','Kode Pakan','Pakan Kg','Air Masuk','Cuaca','Treatment','Teknisi'], _daily_rows(items))


@login_required
@permission_required('operations.daily_records')
def export_daily_records_pdf(request):
    items = DailyPondRecord.objects.select_related('pond', 'technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    rows = _daily_rows(items)
    return export_pdf(
        'laporan_data_harian_kolam', 'Laporan Data Harian Kolam',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kolam', 'DOC', 'Kode Pakan', 'Pakan (Kg)', 'Air Masuk', 'Cuaca', 'Treatment', 'Teknisi'],
        rows,
    )


@login_required
@permission_required('operations.anco')
def anco_checks(request):
    items = AncoCheck.objects.select_related('pond','technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    alerts = items.filter(appetite_status__in=['Nafsu makan turun','Ada sisa pakan']).count()
    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'operations/anco_checks.html', {'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(), 'alerts': alerts})


@login_required
@permission_required('operations.anco')
def add_anco_check(request):
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _anco_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/anco_form.html', {
                'ponds': ponds, 'status_choices': AncoCheck.STATUS_CHOICES,
                'weather_choices': DailyPondRecord.WEATHER_CHOICES, 'obj': payload, 'errors': errors, 'mode': 'add'
            })
        cycle = get_selected_cycle(request, required=True)
        defaults = {
            'technician': request.user,
            'doc': payload['doc'],
            'feed_code': payload['feed_code'],
            'daily_feed_kg': payload['daily_feed_kg'],
            'water_in_cm': payload['water_in_cm'],
            'weather': payload['weather'],
            'treatment': payload['treatment'],
            'anco1_morning': payload['anco1_morning'],
            'anco2_morning': payload['anco2_morning'],
            'anco1_noon': payload['anco1_noon'],
            'anco2_noon': payload['anco2_noon'],
            'anco1_evening': payload['anco1_evening'],
            'anco2_evening': payload['anco2_evening'],
            'notes': payload['notes'],
        }

        # Kompatibilitas data lama: sebelum fitur siklus, data unik hanya
        # berdasarkan kolam dan tanggal. Jika data lama belum mempunyai
        # siklus, gunakan kembali record tersebut dan kaitkan ke siklus aktif.
        obj = AncoCheck.objects.filter(
            cycle=cycle, pond_id=payload['pond_id'], date=payload['date']
        ).first()
        if obj is None:
            obj = AncoCheck.objects.filter(
                cycle__isnull=True, pond_id=payload['pond_id'], date=payload['date']
            ).order_by('pk').first()

        created = obj is None
        if created:
            obj = AncoCheck(
                cycle=cycle, pond_id=payload['pond_id'], date=payload['date']
            )
        else:
            obj.cycle = cycle

        for field, value in defaults.items():
            setattr(obj, field, value)
        obj.save()

        if created:
            messages.success(request, 'Cek anco harian berhasil ditambahkan.')
        else:
            messages.success(request, 'Data Cek Anco pada kolam dan tanggal tersebut sudah ada, sehingga diperbarui tanpa membuat data duplikat.')
        return redirect('operations:anco_checks')
    return render(request, 'operations/anco_form.html', {
        'ponds': ponds, 'status_choices': AncoCheck.STATUS_CHOICES, 'weather_choices': DailyPondRecord.WEATHER_CHOICES, 'mode': 'add'
    })


@login_required
@permission_required('operations.anco')
def export_anco_excel(request):
    items = AncoCheck.objects.select_related('pond','technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    rows = [[
        i.date.strftime('%d/%m/%Y'), i.pond.name, i.feed_code, i.doc, i.daily_feed_kg,
        i.anco1_morning, i.anco2_morning, i.anco1_noon, i.anco2_noon, i.anco1_evening, i.anco2_evening,
        i.water_in_cm, i.weather, i.treatment, i.appetite_status, i.recommendation
    ] for i in items]
    return export_excel(
        'laporan_cek_anco', 'Laporan Cek Anco Harian', f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal','Kolam','Kode Pakan','DOC','P/H','A1 Pagi','A2 Pagi','A1 Siang','A2 Siang','A1 Sore','A2 Sore','Air Masuk Cm','Cuaca','Treatment','Status','Rekomendasi'], rows
    )


@login_required
@permission_required('operations.anco')
def export_anco_pdf(request):
    items = AncoCheck.objects.select_related('pond', 'technician').order_by('-date', 'pond__name')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    rows = []
    alert_count = 0
    for i in items:
        if i.appetite_status in ['Nafsu makan turun', 'Ada sisa pakan']:
            alert_count += 1
        anco_summary = (
            f'Pagi A1:{i.anco1_morning} A2:{i.anco2_morning}\n'
            f'Siang A1:{i.anco1_noon} A2:{i.anco2_noon}\n'
            f'Sore A1:{i.anco1_evening} A2:{i.anco2_evening}'
        )
        rows.append([
            i.date.strftime('%d/%m/%Y'), i.pond.name, i.feed_code or '-', i.doc,
            angka(i.daily_feed_kg, 2), anco_summary,
            f'{angka(i.water_in_cm, 2)} cm' if i.water_in_cm is not None else '-',
            i.weather or '-', i.treatment or '-', i.appetite_status or '-', i.recommendation or '-'
        ])
    total_rows = [['', '', '', '', '', '', '', '', 'Ringkasan', f'{len(rows)} cek', f'{alert_count} alert nafsu makan']]
    return export_pdf(
        'laporan_cek_anco_harian', 'Laporan Cek Anco Harian',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kolam', 'Kode', 'DOC', 'P/H', 'Cek Anco Pagi/Siang/Sore', 'Air Masuk', 'Cuaca', 'Treatment', 'Status', 'Rekomendasi'],
        rows, total_rows,
    )


def _sampling_rows(items):
    return [[
        i.date.strftime('%d/%m/%Y'), i.pond.name, i.doc,
        i.sample_weight_g, i.sample_count,
        i.abw_last_g, i.abw_g, i.abw_target_g, i.target_size, i.size,
        i.adg_weekly_target, i.adg_weekly, i.adg_cumulative,
        i.estimated_sr, i.sr_index_percent,
        i.biomass_kg, i.biomass_index_kg, i.fcr,
        i.population, i.population_index,
        i.cumulative_feed_kg, i.stocking_count, i.daily_feed_kg, i.fr_percent, i.index_score,
        i.harvest_estimation, i.notes
    ] for i in items]


@login_required
@permission_required('operations.sampling')
def sampling_records(request):
    items = SamplingRecord.objects.select_related('pond').order_by('-date', 'pk')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    # Pertahankan formula ABW kondisi terkini: rata-rata satu sampling
    # terbaru dari setiap kolam. Jangan merata-ratakan seluruh histori.
    latest_samples_by_pond = []
    for pond_id in items.values_list('pond_id', flat=True).distinct():
        # Tentukan tanggal sampling paling baru untuk kolam tersebut, lalu
        # gunakan record kanonik (PK paling kecil) bila pernah terbentuk
        # duplikat pada kolam+tanggal yang sama. Tabel juga diurutkan dengan
        # aturan yang sama sehingga nilai kartu selalu sama dengan baris yang
        # ditampilkan kepada pengguna.
        pond_items = items.filter(pond_id=pond_id)
        latest_date = pond_items.order_by('-date').values_list('date', flat=True).first()
        latest_sample = (
            pond_items.filter(date=latest_date).order_by('pk').first()
            if latest_date else None
        )
        if latest_sample is not None:
            latest_samples_by_pond.append(latest_sample)

    avg_abw = (
        sum((Decimal(str(sample.abw_g or 0)) for sample in latest_samples_by_pond), Decimal('0'))
        / Decimal(len(latest_samples_by_pond))
        if latest_samples_by_pond else Decimal('0')
    )
    # FCR pada kartu harus dihitung dari SATU BATCH/TANGGAL sampling
    # terakhir yang sama, sesuai tabel Excel. Jangan mencampur tanggal
    # sampling terakhir yang berbeda antar-kolam karena hasil rata-ratanya
    # dapat berubah (misalnya menjadi 1,12, padahal batch 12/07/2026 = 1,09).
    latest_batch_date = items.order_by('-date').values_list('date', flat=True).first()
    selected_cycle = get_selected_cycle(request)
    latest_batch_samples = []
    if latest_batch_date:
        latest_batch = items.filter(date=latest_batch_date)
        for pond_id in latest_batch.values_list('pond_id', flat=True).distinct():
            pond_batch = latest_batch.filter(pond_id=pond_id)
            sample = None
            if selected_cycle is not None:
                sample = pond_batch.filter(cycle=selected_cycle).order_by('pk').first()
            if sample is None:
                sample = pond_batch.order_by('pk').first()
            if sample is not None:
                latest_batch_samples.append(sample)

    # Hitung FCR kartu dari batch sampling terakhir dengan rumus yang sama
    # seperti Excel: FCR = Pakan Kumulatif / Biomassa Index.
    latest_fcr_values = []
    for sample in latest_batch_samples:
        feed = Decimal(str(sample.cumulative_feed_kg or 0))
        biomass_index = Decimal(str(sample.biomass_index_kg or 0))
        if feed > 0 and biomass_index > 0:
            latest_fcr_values.append(feed / biomass_index)
        elif sample.fcr is not None and Decimal(str(sample.fcr or 0)) > 0:
            # Fallback untuk record lama yang belum memiliki Biomassa Index.
            latest_fcr_values.append(Decimal(str(sample.fcr)))

    avg_fcr = (
        sum(latest_fcr_values, Decimal('0')) / Decimal(len(latest_fcr_values))
        if latest_fcr_values else Decimal('0')
    )

    # ADG pada kartu wajib sama dengan kolom ADG Weekly -> Actual pada
    # baris sampling terbaru tiap kolam. Jangan memakai ADG Accum, target,
    # selisih ABW yang dihitung ulang, maupun seluruh histori sampling.
    latest_adg_actual_values = [
        Decimal(str(sample.adg_weekly))
        for sample in latest_samples_by_pond
        if sample.adg_weekly is not None
    ]
    avg_adg = (
        sum(latest_adg_actual_values, Decimal('0'))
        / Decimal(len(latest_adg_actual_values))
        if latest_adg_actual_values else Decimal('0')
    )
    # Kartu Biomassa FR mengikuti satu BATCH sampling terakhir, bukan
    # sampling terakhir masing-masing kolam yang tanggalnya dapat berbeda.
    # Contoh: jika batch terbaru adalah 12/07/2026, jumlahkan Biomassa FR
    # K1, K2, K3, K5, K6, dan K7 hanya pada tanggal tersebut.
    #
    # Saat masih ada record legacy (cycle=NULL), prioritaskan record yang
    # sudah terikat ke siklus terpilih. Jika terdapat duplikat dalam batch
    # yang sama, gunakan PK terkecil agar konsisten dengan urutan tabel
    # (.order_by('-date', 'pk')).
    biomass = sum(
        (Decimal(str(sample.biomass_kg or 0)) for sample in latest_batch_samples),
        Decimal('0'),
    )

    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'operations/sampling_records.html', {
        'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(),
        'avg_abw': avg_abw, 'avg_fcr': avg_fcr, 'avg_adg': avg_adg, 'biomass': biomass
    })


@login_required
@permission_required('operations.sampling')
def add_sampling_record(request):
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _sampling_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/sampling_form.html', {
                'ponds': ponds,
                'today': timezone.localdate(),
                'pond_meta': _sampling_pond_meta(),
                'errors': errors,
            })
        SamplingRecord.objects.create(
            cycle=get_selected_cycle(request, required=True),
            pond_id=payload['pond_id'],
            date=payload['date'],
            doc=payload['doc'],
            sample_weight_g=payload['sample_weight_g'],
            sample_count=payload['sample_count'],
            adg_weekly_target=payload['adg_weekly_target'],
            cumulative_feed_kg=payload['cumulative_feed_kg'],
            stocking_count=payload['stocking_count'],
            daily_feed_kg=payload['daily_feed_kg'],
            fr_percent=payload['fr_percent'],
            population_index=payload['population_index'],
            index_score=payload['index_score'],
            harvest_estimation=payload['harvest_estimation'],
            notes=payload['notes'],
        )
        messages.success(request, 'Data sampling berhasil disimpan. Semua parameter turunan dari format Excel dihitung otomatis oleh sistem.')
        return redirect('operations:sampling_records')
    return render(request, 'operations/sampling_form.html', {
        'ponds': ponds,
        'today': timezone.localdate(),
        'pond_meta': _sampling_pond_meta(),
    })


@login_required
@permission_required('operations.sampling')
def export_sampling_excel(request):
    items = SamplingRecord.objects.select_related('pond').order_by('-date', 'pk')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    headers = ['Tanggal','Kolam','DOC','SHRIMP Berat (gr)','SHRIMP Jumlah (ekor)','ABW Last','ABW Today','ABW Target','Target Size','Size','ADG Target','ADG Actual','ADG Accum','SR% FR','SR% Index','Biomassa FR','Biomassa Index','FCR','Populasi FR','Populasi Index','Pakan Kumulatif','Tebar','F/D','FR','Index','Estimasi Panen','Catatan']
    return export_excel('laporan_sampling', 'Laporan Sampling Pertumbuhan', f'Periode: {format_date_range(date_from, date_to)}', headers, _sampling_rows(items))


@login_required
@permission_required('operations.sampling')
def export_sampling_pdf(request):
    items = SamplingRecord.objects.select_related('pond').order_by('-date', 'pk')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    return export_pdf('laporan_sampling', 'Laporan Sampling Pertumbuhan', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal','Kolam','DOC','ABW','Size','ADG','SR FR','Biomassa','FCR','Estimasi'], [[r[0],r[1],r[2],r[6],r[9],r[11],r[13],r[15],r[17],r[25]] for r in _sampling_rows(items)])


def _siphon_rows(items):
    return [[i.date.strftime('%d/%m/%Y'), i.pond.name, i.doc, i.dead_count, i.live_count, i.daily_total, i.accumulated_total, i.health_indicator, i.notes] for i in items]


@login_required
@permission_required('operations.siphon')
def siphon_records(request):
    items = SiphonRecord.objects.select_related('pond','technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    dead_total = items.aggregate(s=Sum('dead_count'))['s'] or 0
    daily_total = items.aggregate(s=Sum('daily_total'))['s'] or 0
    risk_count = items.filter(health_indicator__icontains='Risiko').count()
    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'operations/siphon_records.html', {'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(), 'dead_total': dead_total, 'daily_total': daily_total, 'risk_count': risk_count})


@login_required
@permission_required('operations.siphon')
def add_siphon_record(request):
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _siphon_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/siphon_form.html', {
                'ponds': ponds, 'obj': payload, 'errors': errors
            })
        SiphonRecord.objects.update_or_create(
            pond_id=payload['pond_id'], date=payload['date'],
            defaults={
                'technician': request.user,
                'doc': payload['doc'],
                'dead_count': payload['dead_count'],
                'live_count': payload['live_count'],
                'notes': payload['notes'],
            }
        )
        messages.success(request, 'Data siphon berhasil disimpan dan indikator kesehatan diperbarui.')
        return redirect('operations:siphon_records')
    return render(request, 'operations/siphon_form.html', {'ponds': ponds})


@login_required
@permission_required('operations.siphon')
def export_siphon_excel(request):
    items = SiphonRecord.objects.select_related('pond','technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    return export_excel('laporan_siphon', 'Laporan Siphon dan Mortalitas', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal','Kolam','DOC','Mati','Hidup','Jumlah Harian','Akumulasi','Indikator','Catatan'], _siphon_rows(items))


@login_required
@permission_required('operations.siphon')
def export_siphon_pdf(request):
    items = SiphonRecord.objects.select_related('pond','technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    return export_pdf('laporan_siphon', 'Laporan Siphon dan Mortalitas', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal','Kolam','DOC','Mati','Hidup','Total','Akumulasi','Indikator'], [r[:8] for r in _siphon_rows(items)])


# ---------------------------------------------------------------------
# Harvest module.
# ---------------------------------------------------------------------
def _harvest_queryset(request):
    date_from, date_to = get_date_range(request)
    items = Harvest.objects.select_related('pond').order_by('-date')
    items = filter_by_date_range(items, 'date', date_from, date_to)
    pond = request.GET.get('pond') or ''
    if pond:
        items = items.filter(pond_id=pond)
    return items, date_from, date_to


def _harvest_rows(items):
    rows = []
    for i in items:
        rows.append([i.date.strftime('%d/%m/%Y'), i.pond.name, i.harvest_type, i.size_text, float(i.total_kg), i.notes])
    return rows


@login_required
@permission_required('operations.harvests')
def harvests(request):
    items, date_from, date_to = _harvest_queryset(request)
    total_kg = items.aggregate(s=Sum('total_kg'))['s'] or 0
    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'operations/harvests.html', {'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(), 'total_kg': total_kg})


@login_required
@permission_required('operations.harvests')
def export_harvests_excel(request):
    items, date_from, date_to = _harvest_queryset(request)
    rows = _harvest_rows(items)
    total_kg = items.aggregate(s=Sum('total_kg'))['s'] or 0
    return export_excel('laporan_panen', 'Laporan Panen', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal', 'Kolam', 'Jenis Panen', 'Size', 'Total Kg', 'Catatan'], rows, [['', '', '', 'TOTAL', float(total_kg), '']])


@login_required
@permission_required('operations.harvests')
def export_harvests_pdf(request):
    items, date_from, date_to = _harvest_queryset(request)
    rows = _harvest_rows(items)
    total_kg = items.aggregate(s=Sum('total_kg'))['s'] or 0
    return export_pdf('laporan_panen', 'Laporan Panen', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal', 'Kolam', 'Jenis', 'Size', 'Kg', 'Catatan'], rows, [['', '', '', 'TOTAL', total_kg, '']])


@login_required
@permission_required('operations.harvests')
def add_harvest(request):
    ponds = Pond.objects.all()
    if request.method == 'POST':
        payload, errors = _harvest_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/harvest_form.html', {'ponds': ponds, 'obj': payload, 'errors': errors})
        Harvest.objects.create(
            cycle=get_selected_cycle(request, required=True),
            pond_id=payload['pond_id'], date=payload['date'], harvest_type=payload['harvest_type'],
            size_text=payload['size_text'], total_kg=payload['total_kg'], notes=payload['notes']
        )
        messages.success(request, 'Data panen berhasil disimpan.')
        return redirect('operations:harvests')
    return render(request, 'operations/harvest_form.html', {'ponds': ponds})


# ---------------------------------------------------------------------
# CRUD helpers - tombol Edit & Hapus untuk semua modul input operasional.
# ---------------------------------------------------------------------

def _detail_value(value, suffix=''):
    if value in (None, ''):
        return '-'
    return f'{value}{suffix}'


def _record_detail_context(obj, title, subtitle, back_url, edit_url, sections, ai_recommendation=''):
    return {
        'obj': obj,
        'title': title,
        'subtitle': subtitle,
        'back_url': back_url,
        'edit_url': edit_url,
        'sections': sections,
        'ai_recommendation': ai_recommendation or '',
    }


@login_required
@permission_required('operations.daily_records')
def daily_record_detail(request, pk):
    obj = get_object_or_404(DailyPondRecord.objects.select_related('pond', 'technician', 'cycle'), pk=pk)
    sections = [
        {'title': 'Identitas Data', 'icon': 'fa-calendar-day', 'rows': [
            ('Tanggal', obj.date.strftime('%d/%m/%Y')), ('Kolam', obj.pond.name),
            ('Siklus Budidaya', obj.cycle.name if obj.cycle else '-'), ('DOC', obj.doc),
            ('Teknisi', obj.technician.get_full_name() or obj.technician.username if obj.technician else '-'),
        ]},
        {'title': 'Operasional Harian', 'icon': 'fa-clipboard-list', 'rows': [
            ('Kode Pakan', obj.feed_code or '-'), ('Pakan Harian', _detail_value(obj.daily_feed_kg, ' kg')),
            ('Air Masuk', _detail_value(obj.water_in_cm, ' cm')), ('Cuaca', obj.weather or '-'),
            ('Treatment', obj.treatment or '-'), ('Catatan', obj.notes or '-'),
        ]},
    ]
    return render(request, 'operations/record_detail.html', _record_detail_context(
        obj, 'Detail Data Harian Kolam', 'Informasi lengkap pencatatan operasional harian.',
        reverse('operations:daily_records'), reverse('operations:edit_daily_record', args=[obj.pk]), sections))


@login_required
@permission_required('operations.parameters')
def parameter_detail(request, pk):
    obj = get_object_or_404(DailyParameter.objects.select_related('pond', 'technician', 'cycle'), pk=pk)
    sections = [
        {'title': 'Identitas Parameter', 'icon': 'fa-calendar-check', 'rows': [
            ('Tanggal', obj.date.strftime('%d/%m/%Y')), ('Kolam', obj.pond.name),
            ('Siklus Budidaya', obj.cycle.name if obj.cycle else '-'), ('DOC', obj.doc),
            ('Teknisi', obj.technician.get_full_name() or obj.technician.username if obj.technician else '-'),
        ]},
        {'title': 'Tinggi & Visual Air', 'icon': 'fa-water', 'rows': [
            ('Tinggi Air Pagi', _detail_value(obj.water_level_morning_cm or obj.water_level_cm, ' cm')),
            ('Tinggi Air Sore', _detail_value(obj.water_level_evening_cm or obj.water_level_cm, ' cm')),
            ('Warna Air Pagi', obj.water_color_morning or obj.water_color or '-'),
            ('Warna Air Sore', obj.water_color_evening or obj.water_color or '-'),
            ('Kecerahan Pagi', _detail_value(obj.transparency_morning or obj.transparency, ' cm')),
            ('Kecerahan Sore', _detail_value(obj.transparency_evening or obj.transparency, ' cm')),
        ]},
        {'title': 'Kualitas Air', 'icon': 'fa-flask-vial', 'rows': [
            ('Suhu Air', _detail_value(obj.temperature, ' °C')), ('pH Pagi', _detail_value(obj.ph_morning)),
            ('pH Sore', _detail_value(obj.ph_evening)), ('DO Pagi', _detail_value(obj.do_morning, ' mg/L')),
            ('DO Malam', _detail_value(obj.do_night, ' mg/L')), ('Salinitas', _detail_value(obj.salinity, ' ppt')),
            ('Alkalinitas', _detail_value(obj.alkalinity, ' mg/L')), ('Catatan', obj.notes or '-'),
        ]},
    ]
    return render(request, 'operations/record_detail.html', _record_detail_context(
        obj, 'Detail Parameter Harian', 'Data parameter lengkap beserta hasil rekomendasi AI Ollama.',
        reverse('operations:parameters'), reverse('operations:edit_parameter', args=[obj.pk]), sections,
        ai_recommendation=obj.ai_recommendation))


@login_required
@permission_required('operations.anco')
def anco_detail(request, pk):
    obj = get_object_or_404(AncoCheck.objects.select_related('pond', 'technician', 'cycle'), pk=pk)
    sections = [
        {'title': 'Identitas Cek Anco', 'icon': 'fa-calendar-check', 'rows': [
            ('Tanggal', obj.date.strftime('%d/%m/%Y')), ('Kolam', obj.pond.name),
            ('Siklus Budidaya', obj.cycle.name if obj.cycle else '-'), ('DOC', obj.doc),
            ('Teknisi', obj.technician.get_full_name() or obj.technician.username if obj.technician else '-'),
        ]},
        {'title': 'Hasil Pemeriksaan Anco', 'icon': 'fa-table-cells', 'rows': [
            ('Pagi - Anco 1', obj.get_anco1_morning_display()), ('Pagi - Anco 2', obj.get_anco2_morning_display()),
            ('Siang - Anco 1', obj.get_anco1_noon_display()), ('Siang - Anco 2', obj.get_anco2_noon_display()),
            ('Sore - Anco 1', obj.get_anco1_evening_display()), ('Sore - Anco 2', obj.get_anco2_evening_display()),
        ]},
        {'title': 'Analisis Nafsu Makan', 'icon': 'fa-chart-line', 'rows': [
            ('Status Nafsu Makan', obj.appetite_status or '-'), ('Rekomendasi', obj.recommendation or '-'),
            ('Treatment', obj.treatment or '-'), ('Catatan', obj.notes or '-'),
        ]},
    ]
    return render(request, 'operations/record_detail.html', _record_detail_context(
        obj, 'Detail Cek Anco Harian', 'Hasil pemeriksaan anco pagi, siang, sore dan rekomendasinya.',
        reverse('operations:anco_checks'), reverse('operations:edit_anco_check', args=[obj.pk]), sections))


@login_required
@permission_required('operations.sampling')
def sampling_detail(request, pk):
    obj = get_object_or_404(SamplingRecord.objects.select_related('pond', 'cycle'), pk=pk)
    sections = [
        {'title': 'Identitas Sampling', 'icon': 'fa-calendar-check', 'rows': [
            ('Tanggal', obj.date.strftime('%d/%m/%Y')), ('Kolam', obj.pond.name),
            ('Siklus Budidaya', obj.cycle.name if obj.cycle else '-'), ('DOC', obj.doc),
        ]},
        {'title': 'Pertumbuhan Udang', 'icon': 'fa-shrimp', 'rows': [
            ('Berat Sampel', _detail_value(obj.sample_weight_g, ' g')), ('Jumlah Sampel', _detail_value(obj.sample_count, ' ekor')),
            ('ABW Last', _detail_value(obj.abw_last_g, ' g')), ('ABW Today', _detail_value(obj.abw_g, ' g')),
            ('Size', obj.size), ('ADG Mingguan', obj.adg_weekly), ('ADG Kumulatif', obj.adg_cumulative),
        ]},
        {'title': 'Estimasi Produksi', 'icon': 'fa-chart-pie', 'rows': [
            ('Estimasi SR', _detail_value(obj.estimated_sr, ' %')), ('Biomassa FR', _detail_value(obj.biomass_kg, ' kg')),
            ('FCR', obj.fcr), ('Populasi', _detail_value(obj.population, ' ekor')),
            ('Pakan Kumulatif', _detail_value(obj.cumulative_feed_kg, ' kg')), ('Estimasi Panen', obj.harvest_estimation or '-'),
            ('Catatan', obj.notes or '-'),
        ]},
    ]
    return render(request, 'operations/record_detail.html', _record_detail_context(
        obj, 'Detail Data Sampling', 'Informasi lengkap pertumbuhan, biomassa, SR, dan FCR.',
        reverse('operations:sampling_records'), reverse('operations:edit_sampling_record', args=[obj.pk]), sections))


@login_required
@permission_required('operations.siphon')
def siphon_detail(request, pk):
    obj = get_object_or_404(SiphonRecord.objects.select_related('pond', 'technician', 'cycle'), pk=pk)
    sections = [
        {'title': 'Identitas Siphon', 'icon': 'fa-calendar-check', 'rows': [
            ('Tanggal', obj.date.strftime('%d/%m/%Y')), ('Kolam', obj.pond.name),
            ('Siklus Budidaya', obj.cycle.name if obj.cycle else '-'), ('DOC', obj.doc),
            ('Teknisi', obj.technician.get_full_name() or obj.technician.username if obj.technician else '-'),
        ]},
        {'title': 'Hasil Siphon', 'icon': 'fa-shrimp', 'rows': [
            ('Udang Mati', _detail_value(obj.dead_count, ' ekor')), ('Udang Hidup', _detail_value(obj.live_count, ' ekor')),
            ('Jumlah Harian', _detail_value(obj.daily_total, ' ekor')), ('Total Akumulatif', _detail_value(obj.accumulated_total, ' ekor')),
            ('Indikator Kesehatan', obj.health_indicator or '-'), ('Catatan', obj.notes or '-'),
        ]},
    ]
    return render(request, 'operations/record_detail.html', _record_detail_context(
        obj, 'Detail Data Siphon', 'Informasi mortalitas dan indikator kesehatan kolam.',
        reverse('operations:siphon_records'), reverse('operations:edit_siphon_record', args=[obj.pk]), sections))


@login_required
@permission_required('operations.harvests')
def harvest_detail(request, pk):
    obj = get_object_or_404(Harvest.objects.select_related('pond', 'cycle'), pk=pk)
    sections = [
        {'title': 'Detail Panen', 'icon': 'fa-scale-balanced', 'rows': [
            ('Tanggal', obj.date.strftime('%d/%m/%Y')), ('Kolam', obj.pond.name),
            ('Siklus Budidaya', obj.cycle.name if obj.cycle else '-'), ('Jenis Panen', obj.harvest_type),
            ('Size', obj.size_text), ('Total Panen', _detail_value(obj.total_kg, ' kg')), ('Catatan', obj.notes or '-'),
        ]},
    ]
    return render(request, 'operations/record_detail.html', _record_detail_context(
        obj, 'Detail Data Panen', 'Informasi lengkap hasil panen per kolam.',
        reverse('operations:harvests'), reverse('operations:edit_harvest', args=[obj.pk]), sections))

@login_required
@permission_required('operations.daily_records')
def edit_daily_record(request, pk):
    obj = get_object_or_404(DailyPondRecord, pk=pk)
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _daily_record_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/daily_record_form.html', {
                'ponds': ponds, 'weather_choices': DailyPondRecord.WEATHER_CHOICES, 'obj': payload, 'errors': errors, 'mode': 'edit'
            })
        obj.pond_id = payload['pond_id']
        obj.date = payload['date']
        obj.cycle = get_selected_cycle(request, required=True)
        obj.technician = request.user
        obj.doc = payload['doc']
        obj.feed_code = payload['feed_code']
        obj.daily_feed_kg = payload['daily_feed_kg']
        obj.water_in_cm = payload['water_in_cm']
        obj.weather = payload['weather']
        obj.treatment = payload['treatment']
        obj.notes = payload['notes']
        obj.save()
        messages.success(request, 'Data harian kolam berhasil diperbarui.')
        return redirect('operations:daily_records')
    return render(request, 'operations/daily_record_form.html', {'ponds': ponds, 'weather_choices': DailyPondRecord.WEATHER_CHOICES, 'obj': obj, 'mode': 'edit'})

@login_required
@permission_required('operations.daily_records')
@require_POST
def delete_daily_record(request, pk):
    get_object_or_404(DailyPondRecord, pk=pk).delete()
    messages.success(request, 'Data harian kolam berhasil dihapus.')
    return redirect('operations:daily_records')

@login_required
@permission_required('operations.anco')
def edit_anco_check(request, pk):
    obj = get_object_or_404(AncoCheck, pk=pk)
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _anco_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/anco_form.html', {
                'ponds': ponds, 'status_choices': AncoCheck.STATUS_CHOICES,
                'weather_choices': DailyPondRecord.WEATHER_CHOICES, 'obj': obj, 'errors': errors, 'mode': 'edit'
            })
        obj.pond_id = payload['pond_id']
        obj.date = payload['date']
        obj.cycle = get_selected_cycle(request, required=True)
        obj.technician = request.user
        obj.doc = payload['doc']
        obj.feed_code = payload['feed_code']
        obj.daily_feed_kg = payload['daily_feed_kg']
        obj.water_in_cm = payload['water_in_cm']
        obj.weather = payload['weather']
        obj.treatment = payload['treatment']
        obj.anco1_morning = payload['anco1_morning']
        obj.anco2_morning = payload['anco2_morning']
        obj.anco1_noon = payload['anco1_noon']
        obj.anco2_noon = payload['anco2_noon']
        obj.anco1_evening = payload['anco1_evening']
        obj.anco2_evening = payload['anco2_evening']
        obj.notes = payload['notes']
        obj.save()
        messages.success(request, 'Cek anco berhasil diperbarui sesuai format tabel lapangan.')
        return redirect('operations:anco_checks')
    return render(request, 'operations/anco_form.html', {
        'ponds': ponds, 'status_choices': AncoCheck.STATUS_CHOICES,
        'weather_choices': DailyPondRecord.WEATHER_CHOICES, 'obj': obj, 'mode': 'edit'
    })

@login_required
@permission_required('operations.anco')
@require_POST
def delete_anco_check(request, pk):
    get_object_or_404(AncoCheck, pk=pk).delete()
    messages.success(request, 'Data cek anco berhasil dihapus.')
    return redirect('operations:anco_checks')

@login_required
@permission_required('operations.sampling')
def edit_sampling_record(request, pk):
    obj = get_object_or_404(SamplingRecord, pk=pk)
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _sampling_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/sampling_form.html', {
                'ponds': ponds, 'today': timezone.localdate(), 'pond_meta': _sampling_pond_meta(),
                'obj': obj, 'mode': 'edit', 'errors': errors
            })
        obj.pond_id = payload['pond_id']
        obj.date = payload['date']
        obj.cycle = get_selected_cycle(request, required=True)
        obj.doc = payload['doc']
        obj.sample_weight_g = payload['sample_weight_g']
        obj.sample_count = payload['sample_count']
        obj.adg_weekly_target = payload['adg_weekly_target']
        obj.cumulative_feed_kg = payload['cumulative_feed_kg']
        obj.stocking_count = payload['stocking_count']
        obj.daily_feed_kg = payload['daily_feed_kg']
        obj.fr_percent = payload['fr_percent']
        obj.population_index = payload['population_index']
        obj.index_score = payload['index_score']
        obj.harvest_estimation = payload['harvest_estimation']
        obj.notes = payload['notes']
        obj.save()
        messages.success(request, 'Data sampling berhasil diperbarui dan dihitung ulang otomatis.')
        return redirect('operations:sampling_records')
    return render(request, 'operations/sampling_form.html', {'ponds': ponds, 'today': timezone.localdate(), 'pond_meta': _sampling_pond_meta(), 'obj': obj, 'mode': 'edit'})


@login_required
@permission_required('operations.sampling')
@require_POST
def delete_sampling_record(request, pk):
    get_object_or_404(SamplingRecord, pk=pk).delete()
    messages.success(request, 'Data sampling berhasil dihapus.')
    return redirect('operations:sampling_records')

@login_required
@permission_required('operations.siphon')
def edit_siphon_record(request, pk):
    obj = get_object_or_404(SiphonRecord, pk=pk)
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        payload, errors = _siphon_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/siphon_form.html', {
                'ponds': ponds, 'obj': payload, 'errors': errors, 'mode': 'edit'
            })
        obj.pond_id = payload['pond_id']
        obj.date = payload['date']
        obj.cycle = get_selected_cycle(request, required=True)
        obj.technician = request.user
        obj.doc = payload['doc']
        obj.dead_count = payload['dead_count']
        obj.live_count = payload['live_count']
        obj.notes = payload['notes']
        obj.save()
        messages.success(request, 'Data siphon berhasil diperbarui dan indikator kesehatan dihitung ulang.')
        return redirect('operations:siphon_records')
    return render(request, 'operations/siphon_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'obj': obj, 'mode': 'edit'})

@login_required
@permission_required('operations.siphon')
@require_POST
def delete_siphon_record(request, pk):
    get_object_or_404(SiphonRecord, pk=pk).delete()
    messages.success(request, 'Data siphon berhasil dihapus.')
    return redirect('operations:siphon_records')

@login_required
@permission_required('operations.parameters')
def edit_parameter(request, pk):
    obj = get_object_or_404(DailyParameter, pk=pk)
    ponds = Pond.objects.all()
    if request.method == 'POST':
        payload, errors = _parameter_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/parameter_form.html', {
                'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'obj': payload, 'errors': errors, 'mode': 'edit'
            })
        obj.pond_id = payload['pond_id']
        obj.technician = request.user
        obj.date = payload['date']
        obj.cycle = get_selected_cycle(request, required=True)
        obj.doc = payload['doc']
        for field in [
            'feed_code', 'water_in_cm', 'weather',
            'water_level_cm', 'water_level_morning_cm', 'water_level_evening_cm',
            'temperature', 'ph_morning', 'ph_evening', 'do_morning', 'do_night',
            'salinity', 'alkalinity', 'transparency', 'transparency_morning', 'transparency_evening',
            'feed_kg', 'mortality', 'water_color', 'water_color_morning', 'water_color_evening', 'notes'
        ]:
            setattr(obj, field, payload[field])
        if 'analyse' in request.POST:
            obj.ai_recommendation = ask_ollama(_parameter_ai_prompt(obj))
        obj.save()
        messages.success(request, 'Parameter harian berhasil diperbarui.')
        return redirect('operations:parameters')
    return render(request, 'operations/parameter_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'obj': obj, 'mode': 'edit'})


@login_required
@permission_required('operations.parameters')
@require_POST
def delete_parameter(request, pk):
    get_object_or_404(DailyParameter, pk=pk).delete()
    messages.success(request, 'Parameter harian berhasil dihapus.')
    return redirect('operations:parameters')

@login_required
@permission_required('operations.harvests')
def edit_harvest(request, pk):
    obj = get_object_or_404(Harvest, pk=pk)
    ponds = Pond.objects.all()
    if request.method == 'POST':
        payload, errors = _harvest_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/harvest_form.html', {
                'ponds': ponds, 'obj': payload, 'errors': errors, 'mode': 'edit'
            })
        obj.pond_id = payload['pond_id']
        obj.date = payload['date']
        obj.cycle = get_selected_cycle(request, required=True)
        obj.harvest_type = payload['harvest_type']
        obj.size_text = payload['size_text']
        obj.total_kg = payload['total_kg']
        obj.notes = payload['notes']
        obj.save()
        messages.success(request, 'Data panen berhasil diperbarui.')
        return redirect('operations:harvests')
    return render(request, 'operations/harvest_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'obj': obj, 'mode': 'edit'})

@login_required
@permission_required('operations.harvests')
@require_POST
def delete_harvest(request, pk):
    get_object_or_404(Harvest, pk=pk).delete()
    messages.success(request, 'Data panen berhasil dihapus.')
    return redirect('operations:harvests')

# ---------------------------------------------------------------------
# Import Excel operasional: Anco, Sampling, Siphon, Parameter Harian
# ---------------------------------------------------------------------
import os
import tempfile
from io import BytesIO
from django.http import HttpResponse
from django.db import transaction
from accounts.rbac import normalized_roles, is_owner
from .excel_import import parse_workbook, build_template, MODULE_LABELS


def _excel_import_allowed(user):
    if is_owner(user):
        return True
    return 'teknisi' in normalized_roles(user)


def _excel_import_forbidden(request):
    messages.error(request, 'Import Excel hanya dapat digunakan oleh Root, Owner, atau Teknisi.')
    return render(request, 'accounts/forbidden.html', status=403)


def _dec_or_none(value):
    if value in (None, ''): return None
    try: return Decimal(str(value))
    except Exception: return None


def _save_import_rows(request, module, rows, duplicate_mode):
    cycle=get_selected_cycle(request,required=True)
    created=updated=skipped=0
    with transaction.atomic():
        for item in rows:
            if not item.get('valid'): continue
            d=item['data']; lookup={'pond_id':d['pond_id'],'date':d['date']}
            if module in ('anco','sampling','parameter'):
                lookup['cycle']=cycle
            if module=='anco':
                defaults={k:d.get(k) for k in ['doc','feed_code','daily_feed_kg','water_in_cm','weather','treatment','notes','anco1_morning','anco2_morning','anco1_noon','anco2_noon','anco1_evening','anco2_evening']}
                defaults['water_in_cm'] = _dec_or_none(defaults.get('water_in_cm'))
                defaults['technician']=request.user
                obj=AncoCheck.objects.filter(**lookup).first()
                if obj and duplicate_mode=='skip': skipped+=1; continue
                if obj:
                    for k,v in defaults.items(): setattr(obj,k,v)
                    obj.save(); updated+=1
                else:
                    AncoCheck.objects.create(**lookup,**defaults); created+=1
            elif module=='sampling':
                # Normalisasi tipe data sebelum disimpan. Nilai dari session
                # berasal dari JSON sehingga angka Decimal tersimpan sebagai string.
                provided_fields = set(d.get('provided_fields') or [])
                defaults = {
                    'doc': int(d.get('doc') or 0),
                    'sample_weight_g': _dec_or_none(d.get('sample_weight_g')) or Decimal('0'),
                    'sample_count': int(d.get('sample_count') or 0),
                    'abw_last_g': _dec_or_none(d.get('abw_last_g')) or Decimal('0'),
                    'abw_g': _dec_or_none(d.get('abw_g')) or Decimal('0'),
                    'abw_target_g': _dec_or_none(d.get('abw_target_g')) or Decimal('0'),
                    'size': _dec_or_none(d.get('size')) or Decimal('0'),
                    'adg_weekly_target': _dec_or_none(d.get('adg_weekly_target')) or Decimal('0'),
                    # Import wajib memakai rumus (ABW Today - ABW Last) / 7.
                    'adg_weekly': (
                        ((_dec_or_none(d.get('abw_g')) or Decimal('0')) -
                         (_dec_or_none(d.get('abw_last_g')) or Decimal('0'))) / Decimal('7')
                    ).quantize(Decimal('0.001')) if (
                        (_dec_or_none(d.get('abw_g')) or Decimal('0')) and
                        (_dec_or_none(d.get('abw_last_g')) or Decimal('0'))
                    ) else Decimal('0'),
                    'adg_cumulative': _dec_or_none(d.get('adg_cumulative')) or Decimal('0'),
                    'estimated_sr': _dec_or_none(d.get('estimated_sr')) or Decimal('0'),
                    'sr_index_percent': _dec_or_none(d.get('sr_index_percent')) or Decimal('0'),
                    'biomass_kg': _dec_or_none(d.get('biomass_kg')) or Decimal('0'),
                    'biomass_index_kg': _dec_or_none(d.get('biomass_index_kg')) or Decimal('0'),
                    'fcr': _dec_or_none(d.get('fcr')) or Decimal('0'),
                    'population': int(d.get('population') or 0),
                    'cumulative_feed_kg': _dec_or_none(d.get('cumulative_feed_kg')) or Decimal('0'),
                    'stocking_count': int(d.get('stocking_count') or 0),
                    'daily_feed_kg': _dec_or_none(d.get('daily_feed_kg')) or Decimal('0'),
                    'fr_percent': _dec_or_none(d.get('fr_percent')) or Decimal('0'),
                    'population_index': int(d.get('population_index') or 0),
                    'index_score': _dec_or_none(d.get('index_score')) or Decimal('0'),
                    'notes': d.get('notes') or '',
                }

                # Jangan mengosongkan kolom yang tidak tersedia pada template
                # ringkas. Kolom turunan akan dihitung ulang oleh model; kolom
                # tambahan yang tidak dikirim tetap mempertahankan nilai lama.
                if not d.get('preserve_imported_metrics'):
                    keep_when_missing = {
                        'abw_last_g', 'abw_g', 'abw_target_g', 'size',
                        'adg_weekly', 'adg_cumulative', 'estimated_sr',
                        'sr_index_percent', 'biomass_kg', 'biomass_index_kg',
                        'fcr', 'population'
                    }
                    for field in keep_when_missing:
                        if field not in provided_fields:
                            defaults.pop(field, None)

                # Data sampling lama dapat memiliki cycle NULL atau cycle berbeda.
                # Cari dahulu berdasarkan kolam+tanggal agar import benar-benar
                # memperbarui baris yang tampil, bukan membuat duplikat tersembunyi.
                # Gunakan satu record kanonik untuk kombinasi kolam+tanggal.
                # Versi sebelumnya memilih ID paling besar sehingga kartu dapat
                # membaca duplikat yang berbeda dari baris pertama pada tabel.
                matches = SamplingRecord.objects.filter(
                    pond_id=d['pond_id'], date=d['date']
                ).order_by('id')
                obj = matches.first()
                if obj and duplicate_mode == 'skip':
                    skipped += 1
                    continue
                if obj:
                    obj.cycle = cycle
                    for k, v in defaults.items():
                        setattr(obj, k, v)
                    # ADG telah dihitung ulang dari ABW Today dan ABW Last / 7.
                    obj._preserve_imported_metrics = bool(d.get('preserve_imported_metrics'))
                    obj.save()
                    # Hapus duplikat lama setelah record kanonik berhasil disimpan,
                    # agar tabel, kartu, ekspor, dan dashboard membaca data yang sama.
                    matches.exclude(pk=obj.pk).delete()
                    updated += 1
                else:
                    obj = SamplingRecord(
                        cycle=cycle,
                        pond_id=d['pond_id'],
                        date=d['date'],
                        **defaults,
                    )
                    obj._preserve_imported_metrics = bool(d.get('preserve_imported_metrics'))
                    obj.save()
                    created += 1
            elif module=='siphon':
                # Constraint lama unik pond+date, sehingga record lama dipakai kembali.
                obj=SiphonRecord.objects.filter(pond_id=d['pond_id'],date=d['date']).first()
                if obj and duplicate_mode=='skip': skipped+=1; continue
                defaults={'cycle':cycle,'technician':request.user,'doc':d['doc'],'dead_count':d['dead_count'],'live_count':d['live_count'],'notes':d.get('notes','')}
                if obj:
                    for k,v in defaults.items(): setattr(obj,k,v)
                    obj.save(); updated+=1
                else:
                    SiphonRecord.objects.create(pond_id=d['pond_id'],date=d['date'],**defaults); created+=1
            elif module=='parameter':
                defaults={'technician':request.user,'doc':d['doc'],'water_level_morning_cm':_dec_or_none(d.get('water_level_morning_cm')),
                    'water_level_evening_cm':_dec_or_none(d.get('water_level_evening_cm')),'ph_morning':_dec_or_none(d.get('ph_morning')),
                    'ph_evening':_dec_or_none(d.get('ph_evening')),'salinity':_dec_or_none(d.get('salinity')),
                    'water_color_morning':d.get('water_color_morning',''),'water_color_evening':d.get('water_color_evening',''),
                    'transparency_morning':_dec_or_none(d.get('transparency_morning')),'transparency_evening':_dec_or_none(d.get('transparency_evening')),
                    'temperature':_dec_or_none(d.get('temperature')),'do_morning':_dec_or_none(d.get('do_morning')),
                    'do_night':_dec_or_none(d.get('do_night')),'alkalinity':_dec_or_none(d.get('alkalinity')),'notes':d.get('notes','')}
                defaults['water_level_cm']=defaults['water_level_morning_cm'] or defaults['water_level_evening_cm']
                defaults['transparency']=defaults['transparency_morning'] or defaults['transparency_evening']
                defaults['water_color']=defaults['water_color_morning'] or defaults['water_color_evening']
                obj=DailyParameter.objects.filter(**lookup).first()
                if obj and duplicate_mode=='skip': skipped+=1; continue
                if obj:
                    for k,v in defaults.items(): setattr(obj,k,v)
                    obj.save(); updated+=1
                else:
                    DailyParameter.objects.create(**lookup,**defaults); created+=1
    return created,updated,skipped


@login_required
def import_excel(request, module):
    if module not in MODULE_LABELS:
        return redirect('operations:production_dashboard')
    if not _excel_import_allowed(request.user):
        return _excel_import_forbidden(request)
    session_key=f'excel_import_{module}'
    rows=request.session.get(session_key,[])
    if request.method=='POST' and request.POST.get('action')=='confirm':
        mode=request.POST.get('duplicate_mode','update')
        created,updated,skipped=_save_import_rows(request,module,rows,mode)
        request.session.pop(session_key,None)
        messages.success(request,f'Import selesai: {created} dibuat, {updated} diperbarui, {skipped} dilewati.')
        target={'anco':'anco_checks','sampling':'sampling_records','siphon':'siphon_records','parameter':'parameters'}[module]
        return redirect(f'operations:{target}')
    if request.method=='POST' and request.FILES.get('excel_file'):
        upload=request.FILES['excel_file']
        if not upload.name.lower().endswith('.xlsx'):
            messages.error(request,'File harus berformat .xlsx')
        else:
            tmp=None
            try:
                with tempfile.NamedTemporaryFile(suffix='.xlsx',delete=False) as fh:
                    for chunk in upload.chunks(): fh.write(chunk)
                    tmp=fh.name
                rows=parse_workbook(module,tmp)
                request.session[session_key]=rows
                request.session.modified=True
            except Exception as exc:
                rows=[]; messages.error(request,f'File tidak dapat dibaca: {exc}')
            finally:
                if tmp and os.path.exists(tmp): os.unlink(tmp)
    valid_count=sum(1 for x in rows if x.get('valid')); error_count=len(rows)-valid_count
    return render(request,'operations/import_excel.html',{'module':module,'module_label':MODULE_LABELS[module],'rows':rows,'valid_count':valid_count,'error_count':error_count})


@login_required
def download_import_template(request,module):
    if module not in MODULE_LABELS:
        return redirect('operations:production_dashboard')
    if not _excel_import_allowed(request.user):
        return _excel_import_forbidden(request)
    wb=build_template(module); stream=BytesIO(); wb.save(stream); stream.seek(0)
    response=HttpResponse(stream.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']=f'attachment; filename="template_import_{module}.xlsx"'
    return response
