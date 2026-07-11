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
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf
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

def _sampling_pond_meta(cycle=None):
    """Metadata kalkulator sampling yang mengikuti siklus aktif.

    Riwayat sampling, pakan harian, dan tebar dikirim ke form agar nilai
    sebelumnya selalu dihitung terhadap tanggal sampling yang dipilih.
    """
    meta = {}
    for pond in Pond.objects.all().order_by('name'):
        sampling_qs = SamplingRecord.objects.filter(pond=pond)
        stocking_qs = Stocking.objects.filter(pond=pond)
        daily_qs = DailyPondRecord.objects.filter(pond=pond)
        if cycle is not None:
            sampling_qs = sampling_qs.filter(cycle=cycle)
            stocking_qs = stocking_qs.filter(cycle=cycle)
            daily_qs = daily_qs.filter(cycle=cycle)

        samples = list(sampling_qs.order_by('date', 'id').values('id', 'date', 'abw_g', 'doc'))
        stockings = list(stocking_qs.order_by('date', 'id').values('date', 'seed_count'))
        daily_rows = list(daily_qs.order_by('date', 'id').values('date', 'daily_feed_kg', 'doc'))
        latest_sample = samples[-1] if samples else None

        meta[str(pond.id)] = {
            'history': [
                {
                    'id': row['id'],
                    'date': row['date'].isoformat(),
                    'abw': _float(row['abw_g']),
                    'doc': int(row['doc'] or 0),
                }
                for row in samples
            ],
            'stocking_history': [
                {
                    'date': row['date'].isoformat(),
                    'seed_count': int(row['seed_count'] or 0),
                }
                for row in stockings
            ],
            'daily_history': [
                {
                    'date': row['date'].isoformat(),
                    'daily_feed_kg': _float(row['daily_feed_kg']),
                    'doc': int(row['doc'] or 0),
                }
                for row in daily_rows
            ],
            'last_abw': _float(latest_sample['abw_g'] if latest_sample else 0),
            'last_date': latest_sample['date'].isoformat() if latest_sample else '',
            'latest_doc': int(latest_sample['doc']) if latest_sample else 0,
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
    if data['doc'] <= 0:
        errors['DOC'] = 'DOC harus lebih dari 0.'
    if data['sample_weight_g'] <= 0:
        errors['Berat SHRIMP'] = 'Berat SHRIMP harus lebih dari 0 gram.'
    if data['sample_count'] <= 0:
        errors['Jumlah SHRIMP'] = 'Jumlah SHRIMP harus lebih dari 0 ekor.'
    if data['fr_percent'] <= 0:
        errors['FR'] = 'FR harus lebih dari 0 agar biomassa dapat dihitung.'
    if data['stocking_count'] <= 0:
        errors['Tebar'] = 'Jumlah tebar harus lebih dari 0.'
    return data, errors


@login_required
@permission_required('operations.production_dashboard')
def production_dashboard(request):
    ponds = Pond.objects.all().order_by('name')
    today = timezone.localdate()
    daily_today = DailyPondRecord.objects.filter(date=today)
    feed_today = daily_today.aggregate(s=Sum('daily_feed_kg'))['s'] or Decimal('0')
    latest_sampling = SamplingRecord.objects.select_related('pond').order_by('pond_id', '-date')
    sampling_map = {}
    for s in latest_sampling:
        if s.pond_id not in sampling_map:
            sampling_map[s.pond_id] = s
    latest_samples = list(sampling_map.values())[:8]
    avg_abw = SamplingRecord.objects.aggregate(a=Avg('abw_g'))['a'] or 0
    avg_fcr = SamplingRecord.objects.aggregate(a=Avg('fcr'))['a'] or 0
    dead_7d = SiphonRecord.objects.filter(date__gte=today-timedelta(days=7)).aggregate(s=Sum('dead_count'))['s'] or 0
    anco_alerts = AncoCheck.objects.filter(date__gte=today-timedelta(days=3), appetite_status__in=['Nafsu makan turun','Ada sisa pakan']).count()
    active_stocking = Stocking.objects.aggregate(s=Sum('seed_count'))['s'] or 0

    pond_cards = []
    for p in ponds:
        sample = sampling_map.get(p.id)
        siphon = SiphonRecord.objects.filter(pond=p).order_by('-date').first()
        anco = AncoCheck.objects.filter(pond=p).order_by('-date').first()
        daily = DailyPondRecord.objects.filter(pond=p).order_by('-date').first()
        pond_cards.append({'pond': p, 'sample': sample, 'siphon': siphon, 'anco': anco, 'daily': daily})

    context = {
        'ponds': ponds,
        'feed_today': feed_today,
        'avg_abw': avg_abw,
        'avg_fcr': avg_fcr,
        'dead_7d': dead_7d,
        'anco_alerts': anco_alerts,
        'active_stocking': active_stocking,
        'latest_samples': latest_samples,
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
    return render(request, 'operations/parameters.html', {'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all()})


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


def _format_sampling_decimal(value):
    try:
        return f"{Decimal(value or 0):,.3f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return '0,000'


def _sampling_pdf_rows(items):
    rows = []
    for i in items:
        rows.append([
            i.date.strftime('%d/%m/%Y'), i.pond.name, i.doc,
            _format_sampling_decimal(i.sample_weight_g), i.sample_count,
            _format_sampling_decimal(i.abw_last_g), _format_sampling_decimal(i.abw_g),
            _format_sampling_decimal(i.abw_target_g), _format_sampling_decimal(i.target_size),
            _format_sampling_decimal(i.size), _format_sampling_decimal(i.adg_weekly_target),
            _format_sampling_decimal(i.adg_weekly), _format_sampling_decimal(i.adg_cumulative),
            _format_sampling_decimal(i.estimated_sr), _format_sampling_decimal(i.sr_index_percent),
            _format_sampling_decimal(i.biomass_kg), _format_sampling_decimal(i.biomass_index_kg),
            _format_sampling_decimal(i.fcr), i.population, i.population_index,
            _format_sampling_decimal(i.cumulative_feed_kg), i.stocking_count,
            _format_sampling_decimal(i.daily_feed_kg), _format_sampling_decimal(i.fr_percent),
            _format_sampling_decimal(i.index_score), i.harvest_estimation, i.notes,
        ])
    return rows


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
    items = SamplingRecord.objects.select_related('pond').order_by('-date', '-id')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    avg_abw = items.aggregate(a=Avg('abw_g'))['a'] or 0
    avg_fcr = items.aggregate(a=Avg('fcr'))['a'] or 0
    avg_adg = items.aggregate(a=Avg('adg_weekly'))['a'] or 0
    biomass = items.aggregate(s=Sum('biomass_kg'))['s'] or 0
    page_obj = paginate_queryset(request, items, per_page=10)
    return render(request, 'operations/sampling_records.html', {
        'items': page_obj, 'page_obj': page_obj, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(),
        'avg_abw': avg_abw, 'avg_fcr': avg_fcr, 'avg_adg': avg_adg, 'biomass': biomass
    })


@login_required
@permission_required('operations.sampling')
def add_sampling_record(request):
    ponds = Pond.objects.all().order_by('name')
    cycle = get_selected_cycle(request)
    if request.method == 'POST':
        payload, errors = _sampling_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/sampling_form.html', {
                'ponds': ponds,
                'today': timezone.localdate(),
                'pond_meta': _sampling_pond_meta(cycle),
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
        'pond_meta': _sampling_pond_meta(cycle),
    })


@login_required
@permission_required('operations.sampling')
def export_sampling_excel(request):
    items = SamplingRecord.objects.select_related('pond').order_by('-date', '-id')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    headers = ['Tanggal','Kolam','DOC','SHRIMP Berat (gr)','SHRIMP Jumlah (ekor)','ABW Last','ABW Today','ABW Target','Target Size','Size','ADG Target','ADG Actual','ADG Accum','SR% FR','SR% Index','Biomassa FR','Biomassa Index','FCR','Populasi FR','Populasi Index','Pakan Kumulatif','Tebar','F/D','FR','Index','Estimasi Panen','Catatan']
    return export_excel(
        'laporan_sampling', 'Laporan Sampling Pertumbuhan',
        f'Periode: {format_date_range(date_from, date_to)}', headers, _sampling_rows(items),
        number_formats={
            3: '#,##0', 4: '#,##0.000', 5: '#,##0',
            6: '#,##0.000', 7: '#,##0.000', 8: '#,##0.000', 9: '#,##0.000', 10: '#,##0.000',
            11: '#,##0.000', 12: '#,##0.000', 13: '#,##0.000', 14: '#,##0.000', 15: '#,##0.000',
            16: '#,##0.000', 17: '#,##0.000', 18: '#,##0.000', 19: '#,##0', 20: '#,##0',
            21: '#,##0.000', 22: '#,##0', 23: '#,##0.000', 24: '#,##0.000', 25: '#,##0.000',
        },
    )


@login_required
@permission_required('operations.sampling')
def export_sampling_pdf(request):
    items = SamplingRecord.objects.select_related('pond').order_by('-date', '-id')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    pdf_rows = _sampling_pdf_rows(items)
    return export_pdf(
        'laporan_sampling', 'Laporan Sampling Pertumbuhan',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal','Kolam','DOC','ABW','Size','ADG','SR FR','Biomassa','FCR','Estimasi'],
        [[r[0], r[1], r[2], r[6], r[9], r[11], r[13], r[15], r[17], r[25]] for r in pdf_rows],
    )


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


def _sampling_detail_value(value, suffix=''):
    return f'{_format_sampling_decimal(value)}{suffix}'


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
            ('Berat Sampel', _sampling_detail_value(obj.sample_weight_g, ' g')), ('Jumlah Sampel', _detail_value(obj.sample_count, ' ekor')),
            ('ABW Last', _sampling_detail_value(obj.abw_last_g, ' g')), ('ABW Today', _sampling_detail_value(obj.abw_g, ' g')),
            ('Size', _sampling_detail_value(obj.size)), ('ADG Mingguan', _sampling_detail_value(obj.adg_weekly)), ('ADG Kumulatif', _sampling_detail_value(obj.adg_cumulative)),
        ]},
        {'title': 'Estimasi Produksi', 'icon': 'fa-chart-pie', 'rows': [
            ('SR FR', _sampling_detail_value(obj.estimated_sr, ' %')), ('SR Index', _sampling_detail_value(obj.sr_index_percent, ' %')),
            ('Biomassa FR', _sampling_detail_value(obj.biomass_kg, ' kg')), ('Biomassa Index', _sampling_detail_value(obj.biomass_index_kg, ' kg')),
            ('FCR', _sampling_detail_value(obj.fcr)), ('Populasi FR', _detail_value(obj.population, ' ekor')), ('Populasi Index', _detail_value(obj.population_index, ' ekor')),
            ('Pakan Kumulatif', _sampling_detail_value(obj.cumulative_feed_kg, ' kg')), ('FR', _sampling_detail_value(obj.fr_percent, ' %')),
            ('Index', _sampling_detail_value(obj.index_score)), ('Estimasi Panen', obj.harvest_estimation or '-'),
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
    cycle = obj.cycle or get_selected_cycle(request)
    if request.method == 'POST':
        payload, errors = _sampling_payload(request)
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            return render(request, 'operations/sampling_form.html', {
                'ponds': ponds, 'today': timezone.localdate(), 'pond_meta': _sampling_pond_meta(cycle),
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
    return render(request, 'operations/sampling_form.html', {'ponds': ponds, 'today': timezone.localdate(), 'pond_meta': _sampling_pond_meta(cycle), 'obj': obj, 'mode': 'edit'})


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
