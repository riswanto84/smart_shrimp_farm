from decimal import Decimal
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count
from django.shortcuts import render
from django.utils import timezone

from accounts.rbac import permission_required
from ponds.models import Pond
from operations.models import DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord, Harvest, DailyParameter
from sales.models import Sale
from finance.models import OperationalExpense
from .services import ask_ollama, ollama_health


def _num(value, default=0.0):
    try:
        return float(value or 0)
    except Exception:
        return default


def _money(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def _rupiah(value):
    return 'Rp {:,}'.format(_money(value)).replace(',', '.')


def _selected_pond(request):
    ponds = Pond.objects.all().order_by('name')
    pond_id = request.GET.get('pond') or request.POST.get('pond') or ''
    pond = None
    if pond_id:
        pond = ponds.filter(id=pond_id).first()
    if not pond:
        pond = ponds.first()
    return ponds, pond


def _pond_context(pond=None, days=7):
    today = timezone.localdate()
    start = today - timedelta(days=days-1)
    daily = DailyPondRecord.objects.select_related('pond').filter(date__range=(start, today))
    anco = AncoCheck.objects.select_related('pond').filter(date__range=(start, today))
    sampling = SamplingRecord.objects.select_related('pond').filter(date__lte=today)
    siphon = SiphonRecord.objects.select_related('pond').filter(date__range=(start, today))
    params = DailyParameter.objects.select_related('pond').filter(date__lte=today)
    harvests = Harvest.objects.select_related('pond').filter(date__lte=today)
    sales = Sale.objects.filter(date__date__range=(start, today))
    expenses = OperationalExpense.objects.filter(date__range=(start, today))
    if pond:
        daily = daily.filter(pond=pond)
        anco = anco.filter(pond=pond)
        sampling = sampling.filter(pond=pond)
        siphon = siphon.filter(pond=pond)
        params = params.filter(pond=pond)
        harvests = harvests.filter(pond=pond)
    latest_daily = daily.order_by('-date').first() or (DailyPondRecord.objects.filter(pond=pond).order_by('-date').first() if pond else DailyPondRecord.objects.order_by('-date').first())
    latest_anco = anco.order_by('-date').first() or (AncoCheck.objects.filter(pond=pond).order_by('-date').first() if pond else AncoCheck.objects.order_by('-date').first())
    latest_sampling = sampling.order_by('-date').first()
    latest_siphon = siphon.order_by('-date').first() or (SiphonRecord.objects.filter(pond=pond).order_by('-date').first() if pond else SiphonRecord.objects.order_by('-date').first())
    latest_param = params.order_by('-date').first()
    feed_7d = daily.aggregate(s=Sum('daily_feed_kg'))['s'] or Decimal('0')
    dead_7d = siphon.aggregate(s=Sum('dead_count'))['s'] or 0
    live_siphon_7d = siphon.aggregate(s=Sum('live_count'))['s'] or 0
    avg_dead_7d = round(dead_7d / max(siphon.count(), 1), 1)
    revenue_7d = sales.aggregate(s=Sum('total_amount'))['s'] or Decimal('0')
    expense_7d = expenses.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    data = {
        'today': today,
        'start': start,
        'pond': pond,
        'daily_qs': daily,
        'anco_qs': anco,
        'sampling_qs': sampling,
        'siphon_qs': siphon,
        'latest_daily': latest_daily,
        'latest_anco': latest_anco,
        'latest_sampling': latest_sampling,
        'latest_siphon': latest_siphon,
        'latest_param': latest_param,
        'feed_7d': feed_7d,
        'dead_7d': dead_7d,
        'avg_dead_7d': avg_dead_7d,
        'live_siphon_7d': live_siphon_7d,
        'revenue_7d': revenue_7d,
        'expense_7d': expense_7d,
        'profit_7d': revenue_7d - expense_7d,
        'harvests': harvests,
        'sales': sales,
        'expenses': expenses,
    }
    return data


def _risk_and_health(ctx):
    risk = 0
    reasons = []
    p = ctx.get('latest_param')
    s = ctx.get('latest_sampling')
    a = ctx.get('latest_anco')
    if p:
        if p.do_night is not None and _num(p.do_night) < 4:
            risk += 25; reasons.append('DO malam rendah')
        if p.do_morning is not None and _num(p.do_morning) < 4:
            risk += 20; reasons.append('DO pagi rendah')
        ph = _num(p.ph_evening or p.ph_morning)
        if ph and (ph < 7.3 or ph > 8.8):
            risk += 15; reasons.append('pH di luar rentang ideal')
        temp = _num(p.temperature)
        if temp and (temp < 27 or temp > 32):
            risk += 10; reasons.append('Suhu perlu perhatian')
    if ctx['dead_7d'] >= 500:
        risk += 25; reasons.append('Mortalitas 7 hari tinggi')
    elif ctx['dead_7d'] >= 150:
        risk += 15; reasons.append('Mortalitas meningkat')
    if a and a.appetite_status in ['Nafsu makan turun', 'Ada sisa pakan']:
        risk += 20; reasons.append(a.appetite_status)
    if s and _num(s.fcr) > 1.6:
        risk += 10; reasons.append('FCR mulai tinggi')
    risk = min(risk, 100)
    health = max(0, 100 - risk)
    if health >= 80:
        status, risk_label = 'BAIK', 'Rendah'
    elif health >= 60:
        status, risk_label = 'WASPADA', 'Sedang'
    else:
        status, risk_label = 'PERLU TINDAKAN', 'Tinggi'
    return health, status, risk_label, reasons[:5]


def _feed_recommendation(ctx):
    s = ctx.get('latest_sampling')
    a = ctx.get('latest_anco')
    latest_daily = ctx.get('latest_daily')
    biomass = _num(s.biomass_kg if s else 0)
    fr = _num(s.fr_percent if s else 0)
    current_feed = _num(latest_daily.daily_feed_kg if latest_daily else 0)
    if biomass and fr:
        base = biomass * fr / 100
    else:
        base = current_feed or _num(ctx['feed_7d']) / 7
    multiplier = 1.0
    reason = 'Pakan dipertahankan karena data belum menunjukkan perubahan ekstrem.'
    if a and a.appetite_status == 'Nafsu makan baik' and ctx['avg_dead_7d'] < 30:
        multiplier = 1.03
        reason = 'Anco cenderung habis dan mortalitas rendah; kenaikan bertahap 3% masih aman bila kualitas air stabil.'
    elif a and a.appetite_status in ['Ada sisa pakan', 'Nafsu makan turun']:
        multiplier = 0.88
        reason = 'Ada sisa pakan/nafsu makan turun; kurangi pakan sementara dan cek kualitas air.'
    if ctx['dead_7d'] > 150:
        multiplier = min(multiplier, 0.85)
        reason = 'Mortalitas 7 hari meningkat; kurangi pakan dan fokus stabilisasi kolam.'
    total = max(base * multiplier, 0)
    sessions = [round(total*0.26, 1), round(total*0.29, 1), round(total*0.27, 1), round(total*0.18, 1)]
    return round(total, 1), sessions, reason


def _harvest_prediction(ctx, target_size=70, price=63000):
    s = ctx.get('latest_sampling')
    today = ctx['today']
    if not s:
        return {'date': today, 'days': 0, 'target_size': target_size, 'biomass': 0, 'value': 0, 'summary': 'Data sampling belum tersedia.'}
    abw = _num(s.abw_g)
    adg = _num(s.adg_weekly or s.adg_cumulative or 0.15)
    target_abw = 1000 / float(target_size or 70)
    days_needed = 0 if abw >= target_abw else int(max((target_abw - abw) / max(adg, 0.01), 0))
    est_date = today + timedelta(days=days_needed)
    biomass = _num(s.biomass_kg or s.biomass_index_kg)
    value = biomass * price
    summary = f'Prediksi panen parsial size {target_size} sekitar {est_date.strftime("%d/%m/%Y")} dengan estimasi biomassa {biomass:.1f} kg.'
    return {'date': est_date, 'days': days_needed, 'target_size': target_size, 'biomass': round(biomass,1), 'value': value, 'summary': summary, 'sample': s}


def _ai_prompt(title, ctx, extra=''):
    pond_name = ctx['pond'].name if ctx.get('pond') else 'Semua kolam'
    s = ctx.get('latest_sampling')
    a = ctx.get('latest_anco')
    p = ctx.get('latest_param')
    d = ctx.get('latest_daily')
    siphon = ctx.get('latest_siphon')
    return f"""
Anda adalah AI konsultan tambak udang vaname untuk Smart Shrimp Farm. Buat analisa ringkas, praktis, dan berbasis data dalam Bahasa Indonesia.
Fitur: {title}
Kolam: {pond_name}
Periode: {ctx['start']} s.d. {ctx['today']}
Data harian terakhir: DOC {getattr(d,'doc','-')}, pakan harian {getattr(d,'daily_feed_kg','-')} kg, cuaca {getattr(d,'weather','-')}
Anco terakhir: {getattr(a,'appetite_status','-')} - {getattr(a,'recommendation','-')}
Sampling terakhir: ABW {getattr(s,'abw_g','-')} g, Size {getattr(s,'size','-')}, ADG {getattr(s,'adg_weekly','-')}, FCR {getattr(s,'fcr','-')}, Biomassa {getattr(s,'biomass_kg','-')} kg, SR {getattr(s,'estimated_sr','-')}%
Siphon terakhir: mati {getattr(siphon,'dead_count','-')} ekor, hidup {getattr(siphon,'live_count','-')} ekor, indikator {getattr(siphon,'health_indicator','-')}
Parameter air terakhir: DO malam {getattr(p,'do_night','-')}, DO pagi {getattr(p,'do_morning','-')}, pH sore {getattr(p,'ph_evening','-')}, suhu {getattr(p,'temperature','-')}, salinitas {getattr(p,'salinity','-')}
Total pakan 7 hari: {ctx['feed_7d']} kg. Total mati siphon 7 hari: {ctx['dead_7d']} ekor. Omzet 7 hari: {ctx['revenue_7d']}. Biaya 7 hari: {ctx['expense_7d']}.
{extra}
Tulis dengan format:
1. Ringkasan kondisi
2. Risiko utama
3. Rekomendasi tindakan 24-48 jam
4. Catatan untuk owner/investor jika relevan
"""


def _maybe_ollama(request, title, ctx, extra=''):
    if request.GET.get('generate') == '1' or request.method == 'POST':
        return ask_ollama(_ai_prompt(title, ctx, extra))
    return ''


@login_required
@permission_required('chat.view')
def ai_pond_analysis(request):
    ponds, pond = _selected_pond(request)
    ctx = _pond_context(pond)
    health, status, risk_label, reasons = _risk_and_health(ctx)
    ai_text = _maybe_ollama(request, 'AI Analisa Kondisi Kolam', ctx)
    return render(request, 'chat_ai/ai_pond_analysis.html', {
        'ponds': ponds, 'selected_pond': pond, 'ctx': ctx, 'health': health, 'status': status,
        'risk_label': risk_label, 'reasons': reasons, 'ollama_health': ollama_health(), 'ai_text': ai_text,
    })


@login_required
@permission_required('chat.view')
def ai_feed_recommendation(request):
    ponds, pond = _selected_pond(request)
    ctx = _pond_context(pond)
    total_feed, sessions, reason = _feed_recommendation(ctx)
    ai_text = _maybe_ollama(request, 'AI Rekomendasi Pakan Harian', ctx, f'Rekomendasi rule-based saat ini: total {total_feed} kg, sesi {sessions}. Alasan: {reason}')
    return render(request, 'chat_ai/ai_feed_recommendation.html', {
        'ponds': ponds, 'selected_pond': pond, 'ctx': ctx, 'total_feed': total_feed, 'sessions': sessions,
        'reason': reason, 'ollama_health': ollama_health(), 'ai_text': ai_text,
    })


@login_required
@permission_required('chat.view')
def ai_siphon_warning(request):
    ponds, pond = _selected_pond(request)
    ctx = _pond_context(pond)
    health, status, risk_label, reasons = _risk_and_health(ctx)
    risk_score = min(100, max(0, 100-health))
    active_alerts = []
    if ctx['dead_7d'] >= 150: active_alerts.append('Mortalitas 7 hari meningkat')
    if ctx.get('latest_anco') and ctx['latest_anco'].appetite_status in ['Nafsu makan turun','Ada sisa pakan']: active_alerts.append('Nafsu makan turun')
    if ctx.get('latest_param') and _num(ctx['latest_param'].do_night) and _num(ctx['latest_param'].do_night) < 4: active_alerts.append('DO malam rendah')
    ai_text = _maybe_ollama(request, 'AI Early Warning Siphon/Kematian', ctx)
    return render(request, 'chat_ai/ai_siphon_warning.html', {
        'ponds': ponds, 'selected_pond': pond, 'ctx': ctx, 'risk_score': risk_score, 'risk_label': risk_label,
        'reasons': reasons, 'active_alerts': active_alerts, 'ollama_health': ollama_health(), 'ai_text': ai_text,
    })


@login_required
@permission_required('chat.view')
def ai_harvest_prediction(request):
    ponds, pond = _selected_pond(request)
    target_sizes = list(range(100, 24, -5))
    try:
        requested_target_size = int(request.GET.get('target_size') or 70)
    except (TypeError, ValueError):
        requested_target_size = 70
    target_size = requested_target_size if requested_target_size in target_sizes else 70
    price = int(request.GET.get('price') or 63000)
    ctx = _pond_context(pond)
    prediction = _harvest_prediction(ctx, target_size, price)
    ai_text = _maybe_ollama(request, 'AI Prediksi Panen Parsial', ctx, f'Target size {target_size}, harga referensi {price}, prediksi awal: {prediction["summary"]}')
    return render(request, 'chat_ai/ai_harvest_prediction.html', {
        'ponds': ponds, 'selected_pond': pond, 'ctx': ctx, 'prediction': prediction,
        'target_size': target_size, 'target_sizes': target_sizes, 'price': price, 'value_rp': _rupiah(prediction['value']),
        'ollama_health': ollama_health(), 'ai_text': ai_text,
    })


@login_required
@permission_required('chat.view')
def ai_daily_summary(request):
    ponds, pond = _selected_pond(request)
    ctx = _pond_context(pond=None)
    health, status, risk_label, reasons = _risk_and_health(ctx)
    nearest = None
    for p in Pond.objects.all():
        pred = _harvest_prediction(_pond_context(p), 70, 63000)
        if pred.get('sample') and (nearest is None or pred['date'] < nearest['date']):
            nearest = {'pond': p, **pred}
    ai_text = _maybe_ollama(request, 'AI Ringkasan Harian untuk Owner/Investor', ctx)
    return render(request, 'chat_ai/ai_daily_summary.html', {
        'ponds': ponds, 'ctx': ctx, 'health': health, 'status': status, 'risk_label': risk_label, 'reasons': reasons,
        'nearest': nearest, 'revenue_rp': _rupiah(ctx['revenue_7d']), 'expense_rp': _rupiah(ctx['expense_7d']), 'profit_rp': _rupiah(ctx['profit_7d']),
        'ollama_health': ollama_health(), 'ai_text': ai_text,
    })
