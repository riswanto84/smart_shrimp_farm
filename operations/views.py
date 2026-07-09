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


def _selected_pond(request):
    pond = request.GET.get('pond') or ''
    return pond


def _apply_common_filters(request, qs, date_field='date'):
    date_from, date_to = get_date_range(request)
    qs = filter_by_date_range(qs, date_field, date_from, date_to)
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


def _sampling_pond_meta():
    today = timezone.localdate()
    meta = {}
    for pond in Pond.objects.all():
        latest_sample = SamplingRecord.objects.filter(pond=pond).order_by('-date').first()
        stocking = Stocking.objects.filter(pond=pond).order_by('-date').first()
        latest_daily = DailyParameter.objects.filter(pond=pond).order_by('-date', '-created_at').first()
        feed_total = DailyParameter.objects.filter(pond=pond, date__lte=today).aggregate(s=Sum('feed_kg'))['s'] or Decimal('0')
        meta[str(pond.id)] = {
            'last_abw': _float(latest_sample.abw_g if latest_sample else 0),
            'last_date': latest_sample.date.isoformat() if latest_sample else '',
            'stocking_count': int(stocking.seed_count) if stocking else 0,
            'daily_feed_kg': _float(latest_daily.feed_kg if latest_daily else 0),
            'cumulative_feed_kg': _float(feed_total),
            'latest_doc': int(latest_daily.doc) if latest_daily else int(latest_sample.doc) if latest_sample else 0,
        }
    return meta


@login_required
@permission_required('operations.production_dashboard')
def production_dashboard(request):
    ponds = Pond.objects.all().order_by('name')
    today = timezone.localdate()
    daily_today = DailyParameter.objects.filter(date=today)
    feed_today = daily_today.aggregate(s=Sum('feed_kg'))['s'] or Decimal('0')
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
        daily = DailyParameter.objects.filter(pond=p).order_by('-date', '-created_at').first()
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
    """Dashboard manajemen parameter harian kolam.
    Menggantikan menu Data Harian Kolam agar operasional harian terpusat di Parameter Harian.
    """
    ponds = Pond.objects.all().order_by('name')
    items, date_from, date_to = _parameter_queryset(request)
    today = timezone.localdate()
    today_items = DailyParameter.objects.select_related('pond').filter(date=today)
    latest_items = DailyParameter.objects.select_related('pond').order_by('pond_id', '-date', '-created_at')
    latest_by_pond = {}
    for row in latest_items:
        if row.pond_id not in latest_by_pond:
            latest_by_pond[row.pond_id] = row
    total_ponds = ponds.count()
    input_today = today_items.values('pond_id').distinct().count()
    missing_today = max(total_ponds - input_today, 0)
    total_feed = items.aggregate(s=Sum('feed_kg'))['s'] or Decimal('0')
    total_water_in = items.aggregate(s=Sum('water_in_cm'))['s'] or Decimal('0')
    avg_ph_morning = items.aggregate(a=Avg('ph_morning'))['a'] or 0
    avg_ph_evening = items.aggregate(a=Avg('ph_evening'))['a'] or 0
    avg_do_morning = items.aggregate(a=Avg('do_morning'))['a'] or 0
    avg_do_night = items.aggregate(a=Avg('do_night'))['a'] or 0
    avg_salinity = items.aggregate(a=Avg('salinity'))['a'] or 0
    avg_transparency_morning = items.aggregate(a=Avg('transparency_morning'))['a'] or 0
    avg_transparency_evening = items.aggregate(a=Avg('transparency_evening'))['a'] or 0

    pond_status = []
    risk_count = 0
    for p in ponds:
        obj = latest_by_pond.get(p.id)
        status = 'Belum ada data'
        risk = 'muted'
        notes = 'Parameter belum tercatat.'
        if obj:
            risk_flags = []
            if obj.do_morning is not None and obj.do_morning < Decimal('4'):
                risk_flags.append('DO pagi rendah')
            if obj.do_night is not None and obj.do_night < Decimal('4'):
                risk_flags.append('DO malam rendah')
            if obj.ph_morning is not None and (obj.ph_morning < Decimal('7.2') or obj.ph_morning > Decimal('8.5')):
                risk_flags.append('pH pagi di luar rentang')
            if obj.ph_evening is not None and (obj.ph_evening < Decimal('7.2') or obj.ph_evening > Decimal('8.7')):
                risk_flags.append('pH sore di luar rentang')
            if obj.mortality and obj.mortality > 0:
                risk_flags.append('ada mortalitas')
            if risk_flags:
                status = 'Perlu Perhatian'
                risk = 'warning'
                risk_count += 1
                notes = ', '.join(risk_flags[:3])
            else:
                status = 'Stabil'
                risk = 'success'
                notes = 'Parameter terakhir relatif aman.'
        pond_status.append({'pond': p, 'obj': obj, 'status': status, 'risk': risk, 'notes': notes})

    weather_summary = today_items.values('weather').annotate(c=Count('id')).order_by('-c')[:5]
    recent = paginate_queryset(request, items, per_page=8)
    ctx = {
        'ponds': ponds,
        'items': recent,
        'page_obj': recent,
        'date_from': date_from,
        'date_to': date_to,
        'total_ponds': total_ponds,
        'input_today': input_today,
        'missing_today': missing_today,
        'total_feed': total_feed,
        'total_water_in': total_water_in,
        'avg_ph_morning': avg_ph_morning,
        'avg_ph_evening': avg_ph_evening,
        'avg_do_morning': avg_do_morning,
        'avg_do_night': avg_do_night,
        'avg_salinity': avg_salinity,
        'avg_transparency_morning': avg_transparency_morning,
        'avg_transparency_evening': avg_transparency_evening,
        'risk_count': risk_count,
        'pond_status': pond_status,
        'weather_summary': weather_summary,
    }
    return render(request, 'operations/parameter_dashboard.html', ctx)

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
# Fitur Data Harian Kolam dinonaktifkan. Data harian dipusatkan di Parameter Harian.
# ---------------------------------------------------------------------
@login_required
def daily_records_redirect(request):
    messages.info(request, 'Fitur Data Harian Kolam sudah digabung ke Parameter Harian. Gunakan Dashboard Parameter Harian Kolam.')
    return redirect('operations:parameter_dashboard')

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
        DailyPondRecord.objects.update_or_create(
            pond_id=request.POST['pond'], date=request.POST['date'],
            defaults={
                'technician': request.user,
                'doc': request.POST.get('doc') or 0,
                'feed_code': request.POST.get('feed_code',''),
                'daily_feed_kg': request.POST.get('daily_feed_kg') or 0,
                'water_in_cm': request.POST.get('water_in_cm') or None,
                'weather': request.POST.get('weather',''),
                'treatment': request.POST.get('treatment',''),
                'notes': request.POST.get('notes',''),
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




def _anco_payload(request):
    errors = {}
    valid_status = {c[0] for c in AncoCheck.STATUS_CHOICES}
    data = {
        'pond_id': request.POST.get('pond'),
        'date': request.POST.get('date'),
        'doc': _parse_int_input(request.POST.get('doc'), 'DOC', errors, min_value=0),
        'feed_code': request.POST.get('feed_code','').strip(),
        'daily_feed_kg': _parse_decimal_input(request.POST.get('daily_feed_kg') or '0', 'P/H Pakan Harian', errors, min_value=0) or Decimal('0'),
        'water_in_cm': _parse_decimal_input(request.POST.get('water_in_cm'), 'Air Masuk', errors, min_value=0),
        'weather': request.POST.get('weather','').strip(),
        'treatment': request.POST.get('treatment','').strip(),
        'anco1_morning': request.POST.get('anco1_morning','-'),
        'anco2_morning': request.POST.get('anco2_morning','-'),
        'anco1_noon': request.POST.get('anco1_noon','-'),
        'anco2_noon': request.POST.get('anco2_noon','-'),
        'anco1_evening': request.POST.get('anco1_evening','-'),
        'anco2_evening': request.POST.get('anco2_evening','-'),
        'notes': request.POST.get('notes','').strip(),
    }
    if not data['pond_id']:
        errors['Kolam'] = 'Kolam wajib dipilih.'
    if not data['date']:
        errors['Tanggal'] = 'Tanggal wajib diisi.'
    if data.get('feed_code') and len(data['feed_code']) > 80:
        errors['Kode Pakan'] = 'Kode pakan maksimal 80 karakter.'
    if data.get('weather') and data['weather'] not in [c[0] for c in DailyParameter.WEATHER_CHOICES]:
        errors['Cuaca'] = 'Cuaca harus dipilih dari daftar.'
    for key in ['anco1_morning','anco2_morning','anco1_noon','anco2_noon','anco1_evening','anco2_evening']:
        if data[key] not in valid_status:
            errors[key] = 'Status anco harus H, S, SS, atau Tidak Dicek.'
    return data, errors

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
            return render(request, 'operations/anco_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'status_choices': AncoCheck.STATUS_CHOICES, 'obj': payload, 'errors': errors})
        AncoCheck.objects.update_or_create(
            pond_id=payload['pond_id'], date=payload['date'],
            defaults={
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
        )
        messages.success(request, 'Cek anco berhasil disimpan dan dianalisa otomatis.')
        return redirect('operations:anco_checks')
    return render(request, 'operations/anco_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'status_choices': AncoCheck.STATUS_CHOICES})


@login_required
@permission_required('operations.anco')
def export_anco_excel(request):
    items = AncoCheck.objects.select_related('pond','technician').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    rows = [[i.date.strftime('%d/%m/%Y'), i.pond.name, i.feed_code, i.doc, i.daily_feed_kg, i.anco1_morning, i.anco2_morning, i.anco1_noon, i.anco2_noon, i.anco1_evening, i.anco2_evening, i.water_in_cm or '', i.weather, i.treatment, i.appetite_status, i.recommendation] for i in items]
    return export_excel('laporan_cek_anco', 'Laporan Cek Anco Harian', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal','Kolam','Kode Pakan','DOC','P/H','A1 Pagi','A2 Pagi','A1 Siang','A2 Siang','A1 Sore','A2 Sore','Air Masuk Cm','Cuaca','Treatment','Status','Rekomendasi'], rows)


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
    items = SamplingRecord.objects.select_related('pond').order_by('-date')
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
    if request.method == 'POST':
        SamplingRecord.objects.create(
            pond_id=request.POST['pond'],
            date=request.POST['date'],
            doc=request.POST.get('doc') or 0,
            sample_weight_g=request.POST.get('sample_weight_g') or 0,
            sample_count=request.POST.get('sample_count') or 0,
            adg_weekly_target=request.POST.get('adg_weekly_target') or 0,
            cumulative_feed_kg=request.POST.get('cumulative_feed_kg') or 0,
            stocking_count=request.POST.get('stocking_count') or 0,
            daily_feed_kg=request.POST.get('daily_feed_kg') or 0,
            fr_percent=request.POST.get('fr_percent') or 0,
            population_index=request.POST.get('population_index') or 0,
            index_score=request.POST.get('index_score') or 0,
            harvest_estimation=request.POST.get('harvest_estimation',''),
            notes=request.POST.get('notes',''),
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
    items = SamplingRecord.objects.select_related('pond').order_by('-date')
    items, date_from, date_to, pond = _apply_common_filters(request, items)
    headers = ['Tanggal','Kolam','DOC','SHRIMP Berat (gr)','SHRIMP Jumlah (ekor)','ABW Last','ABW Today','ABW Target','Target Size','Size','ADG Target','ADG Actual','ADG Accum','SR% FR','SR% Index','Biomassa FR','Biomassa Index','FCR','Populasi FR','Populasi Index','Pakan Kumulatif','Tebar','F/D','FR','Index','Estimasi Panen','Catatan']
    return export_excel('laporan_sampling', 'Laporan Sampling Pertumbuhan', f'Periode: {format_date_range(date_from, date_to)}', headers, _sampling_rows(items))


@login_required
@permission_required('operations.sampling')
def export_sampling_pdf(request):
    items = SamplingRecord.objects.select_related('pond').order_by('-date')
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
        SiphonRecord.objects.update_or_create(
            pond_id=request.POST['pond'], date=request.POST['date'],
            defaults={
                'technician': request.user,
                'doc': request.POST.get('doc') or 0,
                'dead_count': request.POST.get('dead_count') or 0,
                'live_count': request.POST.get('live_count') or 0,
                'notes': request.POST.get('notes',''),
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
        Harvest.objects.create(pond_id=request.POST['pond'], date=request.POST['date'], harvest_type=request.POST.get('harvest_type', 'Parsial'), size_text=request.POST.get('size_text', ''), total_kg=request.POST.get('total_kg') or 0, notes=request.POST.get('notes', ''))
        return redirect('operations:harvests')
    return render(request, 'operations/harvest_form.html', {'ponds': ponds})


# ---------------------------------------------------------------------
# CRUD helpers - tombol Edit & Hapus untuk semua modul input operasional.
# ---------------------------------------------------------------------
@login_required
@permission_required('operations.daily_records')
def edit_daily_record(request, pk):
    obj = get_object_or_404(DailyPondRecord, pk=pk)
    ponds = Pond.objects.all().order_by('name')
    if request.method == 'POST':
        obj.pond_id = request.POST['pond']
        obj.date = request.POST['date']
        obj.technician = request.user
        obj.doc = request.POST.get('doc') or 0
        obj.feed_code = request.POST.get('feed_code','')
        obj.daily_feed_kg = _post_decimal(request.POST.get('daily_feed_kg') or 0)
        obj.water_in_cm = _post_decimal(request.POST.get('water_in_cm')) if request.POST.get('water_in_cm') else None
        obj.weather = request.POST.get('weather','')
        obj.treatment = request.POST.get('treatment','')
        obj.notes = request.POST.get('notes','')
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
            return render(request, 'operations/anco_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'status_choices': AncoCheck.STATUS_CHOICES, 'obj': payload, 'errors': errors, 'mode': 'edit'})
        obj.pond_id = payload['pond_id']
        obj.date = payload['date']
        obj.technician = request.user
        for field in ['doc','feed_code','daily_feed_kg','water_in_cm','weather','treatment','anco1_morning','anco2_morning','anco1_noon','anco2_noon','anco1_evening','anco2_evening','notes']:
            setattr(obj, field, payload[field])
        obj.save()
        messages.success(request, 'Cek anco berhasil diperbarui dan dianalisa ulang.')
        return redirect('operations:anco_checks')
    return render(request, 'operations/anco_form.html', {'ponds': ponds, 'weather_choices': DailyParameter.WEATHER_CHOICES, 'status_choices': AncoCheck.STATUS_CHOICES, 'obj': obj, 'mode': 'edit'})

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
        obj.pond_id = request.POST['pond']
        obj.date = request.POST['date']
        obj.doc = request.POST.get('doc') or 0
        obj.sample_weight_g = _post_decimal(request.POST.get('sample_weight_g') or 0)
        obj.sample_count = request.POST.get('sample_count') or 0
        obj.adg_weekly_target = _post_decimal(request.POST.get('adg_weekly_target') or 0)
        obj.cumulative_feed_kg = _post_decimal(request.POST.get('cumulative_feed_kg') or 0)
        obj.stocking_count = request.POST.get('stocking_count') or 0
        obj.daily_feed_kg = _post_decimal(request.POST.get('daily_feed_kg') or 0)
        obj.fr_percent = _post_decimal(request.POST.get('fr_percent') or 0)
        obj.population_index = int(float(_post_decimal(request.POST.get('population_index') or 0)))
        obj.index_score = _post_decimal(request.POST.get('index_score') or 0)
        obj.harvest_estimation = request.POST.get('harvest_estimation','')
        obj.notes = request.POST.get('notes','')
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
        obj.pond_id = request.POST['pond']
        obj.date = request.POST['date']
        obj.technician = request.user
        obj.doc = request.POST.get('doc') or 0
        obj.dead_count = request.POST.get('dead_count') or 0
        obj.live_count = request.POST.get('live_count') or 0
        obj.notes = request.POST.get('notes','')
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
        obj.pond_id = request.POST['pond']
        obj.date = request.POST['date']
        obj.harvest_type = request.POST.get('harvest_type', 'Parsial')
        obj.size_text = request.POST.get('size_text', '')
        obj.total_kg = _post_decimal(request.POST.get('total_kg') or 0)
        obj.notes = request.POST.get('notes', '')
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
