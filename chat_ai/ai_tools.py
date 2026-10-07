"""Read-only tools that expose Smart Shrimp Farm data to Ollama.

The LLM never receives database credentials and never executes SQL.  Every
operation goes through Django ORM and is constrained to the selected cycle
(and, when supplied, the selected pond).
"""
from datetime import date, timedelta
from decimal import Decimal
import json

from django.db.models import Sum, Avg, Count
from django.utils import timezone

from cultivation.models import CultivationCycle
from ponds.models import Pond
from operations.models import (
    Stocking, DailyParameter, Treatment, FeedLog, Harvest,
    DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord,
)
from sales.models import Sale
from finance.models import OperationalExpense, OtherRevenue, TradeAccount
from finance.services.profit_loss import calculate_profit_loss


def _dec(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _date(v):
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        return None


def _cycle(cycle_id):
    if cycle_id:
        return CultivationCycle.objects.filter(pk=cycle_id).first()
    return (CultivationCycle.objects.filter(status__in=['preparation', 'active', 'harvest'])
            .order_by('-start_date', '-id').first() or CultivationCycle.objects.order_by('-start_date', '-id').first())


def _pond(pond_id):
    return Pond.objects.filter(pk=pond_id).first() if pond_id else None


def _scope(model, cycle_id, pond_id=None):
    qs = model.objects.all()
    if hasattr(model, 'cycle_id') and cycle_id:
        qs = qs.filter(cycle_id=cycle_id)
    if pond_id and hasattr(model, 'pond_id'):
        qs = qs.filter(pond_id=pond_id)
    return qs


def _serialize_date(v):
    return v.isoformat() if v else None


def get_active_cycle(cycle_id=None):
    cycle = _cycle(cycle_id)
    if not cycle:
        return {'status': 'no_data', 'message': 'Belum ada siklus budidaya.'}
    return {
        'status': 'ok', 'cycle_id': cycle.id, 'name': cycle.name,
        'status_cycle': cycle.status, 'start_date': _serialize_date(cycle.start_date),
        'target_end_date': _serialize_date(cycle.target_end_date),
        'target_doc': cycle.target_doc, 'target_size': _dec(cycle.target_size),
        'target_biomass_ton': _dec(cycle.target_biomass_ton),
        'target_sr_percent': _dec(cycle.target_sr_percent),
        'target_fcr': _dec(cycle.target_fcr), 'target_adg': _dec(cycle.target_adg),
    }


def get_pond_overview(cycle_id=None, pond_id=None):
    cycle = _cycle(cycle_id)
    qs = Pond.objects.all().order_by('name')
    if pond_id:
        qs = qs.filter(pk=pond_id)
    rows = []
    for pond in qs:
        stocking = _scope(Stocking, cycle.id if cycle else None, pond.id).order_by('-date').first()
        sampling = _scope(SamplingRecord, cycle.id if cycle else None, pond.id).order_by('-date').first()
        parameter = _scope(DailyParameter, cycle.id if cycle else None, pond.id).order_by('-date', '-created_at').first()
        anco = _scope(AncoCheck, cycle.id if cycle else None, pond.id).order_by('-date').first()
        rows.append({
            'pond_id': pond.id, 'pond': pond.name, 'status': pond.status,
            'stocking_count': stocking.seed_count if stocking else 0,
            'stocking_date': _serialize_date(stocking.date) if stocking else None,
            'latest_sampling_date': _serialize_date(sampling.date) if sampling else None,
            'abw_g': _dec(sampling.abw_g) if sampling else 0,
            'size': _dec(sampling.size) if sampling else 0,
            'adg': _dec(sampling.adg_weekly) if sampling else 0,
            'fcr': _dec(sampling.fcr) if sampling else 0,
            'sr_percent': _dec(sampling.estimated_sr) if sampling else 0,
            'biomass_kg': _dec(sampling.biomass_index_kg or sampling.biomass_kg) if sampling else 0,
            'do_morning': _dec(parameter.do_morning) if parameter else 0,
            'do_night': _dec(parameter.do_night) if parameter else 0,
            'ph_morning': _dec(parameter.ph_morning) if parameter else 0,
            'ph_evening': _dec(parameter.ph_evening) if parameter else 0,
            'anco_status': anco.appetite_status if anco else 'Belum ada data',
        })
    return {'status': 'ok', 'cycle': cycle.name if cycle else None, 'ponds': rows}


def get_stocking_data(cycle_id=None, pond_id=None):
    cycle = _cycle(cycle_id)
    rows = _scope(Stocking, cycle.id if cycle else None, pond_id).order_by('pond__name', '-date')
    return {'status': 'ok', 'cycle': cycle.name if cycle else None, 'records': [
        {'pond_id': r.pond_id, 'pond': r.pond.name, 'date': _serialize_date(r.date),
         'seed_count': r.seed_count, 'hatchery': r.hatchery, 'notes': r.notes}
        for r in rows[:200]
    ]}


def get_water_quality(cycle_id=None, pond_id=None, days=7):
    cycle = _cycle(cycle_id)
    end = timezone.localdate(); start = end - timedelta(days=max(1, min(int(days or 7), 90)) - 1)
    qs = _scope(DailyParameter, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    return {'status': 'ok', 'cycle': cycle.name if cycle else None, 'days': (start.isoformat(), end.isoformat()), 'records': [
        {'pond': r.pond.name, 'date': _serialize_date(r.date), 'doc': r.doc,
         'temperature': _dec(r.temperature), 'ph_morning': _dec(r.ph_morning),
         'ph_evening': _dec(r.ph_evening), 'do_morning': _dec(r.do_morning),
         'do_night': _dec(r.do_night), 'salinity': _dec(r.salinity),
         'alkalinity': _dec(r.alkalinity), 'water_level_morning_cm': _dec(r.water_level_morning_cm),
         'water_level_evening_cm': _dec(r.water_level_evening_cm)}
        for r in qs[:300]
    ]}


def get_feed_history(cycle_id=None, pond_id=None, days=30):
    """Use Anco P/H first; fall back to FeedLog then DailyPondRecord.

    This prevents the old empty DailyPondRecord table from making AI report
    zero feed when the actual field feed is stored in AncoCheck.daily_feed_kg.
    """
    cycle = _cycle(cycle_id)
    end = timezone.localdate(); start = end - timedelta(days=max(1, min(int(days or 30), 365)) - 1)
    anco = _scope(AncoCheck, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).values('pond_id', 'pond__name', 'date', 'daily_feed_kg', 'feed_code').order_by('-date')
    anco_rows = list(anco)
    if anco_rows:
        total = sum(_dec(r['daily_feed_kg']) for r in anco_rows)
        return {'status': 'ok', 'source': 'AncoCheck.daily_feed_kg', 'total_feed_kg': round(total, 2), 'records': [
            {'pond': r['pond__name'], 'date': _serialize_date(r['date']), 'feed_kg': _dec(r['daily_feed_kg']), 'feed_code': r['feed_code']}
            for r in anco_rows[:365]
        ]}
    feed = _scope(FeedLog, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    feed_rows = list(feed[:365])
    if feed_rows:
        return {'status': 'ok', 'source': 'FeedLog', 'total_feed_kg': round(sum(_dec(r.quantity_kg) for r in feed_rows), 2), 'records': [
            {'pond': r.pond.name, 'date': _serialize_date(r.date), 'feed_kg': _dec(r.quantity_kg), 'feed_name': r.feed_name}
            for r in feed_rows
        ]}
    daily = _scope(DailyPondRecord, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    daily_rows = list(daily[:365])
    return {'status': 'ok', 'source': 'DailyPondRecord.daily_feed_kg', 'total_feed_kg': round(sum(_dec(r.daily_feed_kg) for r in daily_rows), 2), 'records': [
        {'pond': r.pond.name, 'date': _serialize_date(r.date), 'feed_kg': _dec(r.daily_feed_kg), 'feed_code': r.feed_code}
        for r in daily_rows
    ]}


def get_anco_history(cycle_id=None, pond_id=None, days=14):
    cycle = _cycle(cycle_id)
    end = timezone.localdate(); start = end - timedelta(days=max(1, min(int(days or 14), 180)) - 1)
    qs = _scope(AncoCheck, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    return {'status': 'ok', 'records': [
        {'pond': r.pond.name, 'date': _serialize_date(r.date), 'feed_kg': _dec(r.daily_feed_kg),
         'morning': [r.anco1_morning, r.anco2_morning], 'noon': [r.anco1_noon, r.anco2_noon],
         'evening': [r.anco1_evening, r.anco2_evening], 'appetite_status': r.appetite_status,
         'recommendation': r.recommendation, 'treatment': r.treatment}
        for r in qs[:250]
    ]}


def get_sampling_history(cycle_id=None, pond_id=None, days=90):
    cycle = _cycle(cycle_id)
    end = timezone.localdate(); start = end - timedelta(days=max(1, min(int(days or 90), 730)) - 1)
    qs = _scope(SamplingRecord, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    return {'status': 'ok', 'records': [
        {'pond': r.pond.name, 'date': _serialize_date(r.date), 'doc': r.doc,
         'abw_g': _dec(r.abw_g), 'size': _dec(r.size), 'adg_weekly': _dec(r.adg_weekly),
         'adg_cumulative': _dec(r.adg_cumulative), 'fcr': _dec(r.fcr),
         'sr_percent': _dec(r.estimated_sr), 'sr_index_percent': _dec(r.sr_index_percent),
         'biomass_kg': _dec(r.biomass_kg), 'biomass_index_kg': _dec(r.biomass_index_kg),
         'population': r.population, 'population_index': r.population_index,
         'cumulative_feed_kg': _dec(r.cumulative_feed_kg), 'daily_feed_kg': _dec(r.daily_feed_kg),
         'fr_percent': _dec(r.fr_percent), 'index_score': _dec(r.index_score),
         'harvest_estimation': r.harvest_estimation}
        for r in qs[:300]
    ]}


def get_siphon_history(cycle_id=None, pond_id=None, days=30):
    cycle = _cycle(cycle_id)
    end = timezone.localdate(); start = end - timedelta(days=max(1, min(int(days or 30), 365)) - 1)
    qs = _scope(SiphonRecord, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    return {'status': 'ok', 'records': [
        {'pond': r.pond.name, 'date': _serialize_date(r.date), 'dead_count': r.dead_count,
         'live_count': r.live_count, 'daily_total': r.daily_total,
         'accumulated_total': r.accumulated_total, 'health_indicator': r.health_indicator,
         'notes': r.notes}
        for r in qs[:365]
    ]}


def get_treatment_history(cycle_id=None, pond_id=None, days=90):
    cycle = _cycle(cycle_id)
    end = timezone.localdate(); start = end - timedelta(days=max(1, min(int(days or 90), 730)) - 1)
    qs = _scope(Treatment, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    return {'status': 'ok', 'records': [
        {'pond': r.pond.name, 'date': _serialize_date(r.date), 'name': r.name, 'dose': r.dose, 'notes': r.notes}
        for r in qs[:300]
    ]}


def get_harvest_history(cycle_id=None, pond_id=None, days=365):
    cycle = _cycle(cycle_id)
    end = timezone.localdate(); start = end - timedelta(days=max(1, min(int(days or 365), 1825)) - 1)
    qs = _scope(Harvest, cycle.id if cycle else None, pond_id).filter(date__range=(start, end)).order_by('-date')
    return {'status': 'ok', 'total_kg': round(sum(_dec(r.total_kg) for r in qs), 2), 'records': [
        {'pond': r.pond.name, 'date': _serialize_date(r.date), 'harvest_type': r.harvest_type,
         'size': r.size_text, 'total_kg': _dec(r.total_kg), 'notes': r.notes}
        for r in qs[:300]
    ]}


def get_production_summary(cycle_id=None, pond_id=None):
    cycle = _cycle(cycle_id)
    sampling = _scope(SamplingRecord, cycle.id if cycle else None, pond_id).order_by('date')
    latest = sampling.order_by('-date').first()
    harvest = _scope(Harvest, cycle.id if cycle else None, pond_id).aggregate(total=Sum('total_kg'))['total'] or Decimal('0')
    feed = _scope(AncoCheck, cycle.id if cycle else None, pond_id).aggregate(total=Sum('daily_feed_kg'))['total'] or Decimal('0')
    if not feed:
        feed = _scope(FeedLog, cycle.id if cycle else None, pond_id).aggregate(total=Sum('quantity_kg'))['total'] or Decimal('0')
    stocking = _scope(Stocking, cycle.id if cycle else None, pond_id).aggregate(total=Sum('seed_count'))['total'] or 0
    siphon_dead = _scope(SiphonRecord, cycle.id if cycle else None, pond_id).aggregate(total=Sum('dead_count'))['total'] or 0
    return {'status': 'ok', 'cycle': cycle.name if cycle else None,
            'stocking_count': stocking, 'feed_total_kg': _dec(feed), 'harvest_total_kg': _dec(harvest),
            'siphon_dead_count': siphon_dead,
            'latest': ({'pond': latest.pond.name, 'date': _serialize_date(latest.date), 'abw_g': _dec(latest.abw_g),
                        'adg': _dec(latest.adg_weekly), 'fcr': _dec(latest.fcr),
                        'sr_percent': _dec(latest.estimated_sr),
                        'biomass_kg': _dec(latest.biomass_index_kg or latest.biomass_kg),
                        'population': latest.population_index or latest.population} if latest else None)}


def get_financial_summary(cycle_id=None, date_from=None, date_to=None):
    cycle = _cycle(cycle_id)
    start = _date(date_from) or (cycle.start_date if cycle else date(2000, 1, 1))
    end = _date(date_to) or timezone.localdate()
    # Use the application's authoritative P&L engine so AI numbers stay
    # consistent with the Finance/P&L screen, including depreciation rules.
    result = calculate_profit_loss(cycle=cycle, date_from=start, date_to=end)
    return {
        'status': 'ok', 'cycle': cycle.name if cycle else None,
        'period': {'from': start.isoformat(), 'to': end.isoformat()},
        'sales_revenue': _dec(result['sales_revenue']),
        'other_revenue': _dec(result['other_revenue']),
        'operating_expense_before_depreciation': _dec(result['operating_expense_before_depreciation']),
        'depreciation': _dec(result['depreciation_total']),
        'total_expense': _dec(result['expense_total']),
        'profit': _dec(result['profit']),
        'category_totals': {k: _dec(v) for k, v in result['category_totals'].items()},
        'sales_count': result['sales_queryset'].count(),
        'expense_count': result['expense_queryset'].count(),
    }


def get_receivables_payables(cycle_id=None):
    cycle = _cycle(cycle_id)
    qs = TradeAccount.objects.all()
    if cycle:
        qs = qs.filter(cycle=cycle)
    rows = []
    receivable = payable = Decimal('0')
    for r in qs:
        outstanding = r.outstanding_amount
        if outstanding <= 0:
            continue
        if r.account_type == TradeAccount.RECEIVABLE:
            receivable += outstanding
        else:
            payable += outstanding
        rows.append({'type': r.account_type, 'partner': r.partner_name, 'description': r.description,
                     'due_date': _serialize_date(r.due_date), 'original_amount': _dec(r.original_amount),
                     'paid_amount': _dec(r.paid_amount), 'outstanding': _dec(outstanding),
                     'overdue': r.is_overdue})
    return {'status': 'ok', 'receivable_outstanding': _dec(receivable), 'payable_outstanding': _dec(payable), 'records': rows[:300]}


TOOLS = {
    'get_active_cycle': get_active_cycle,
    'get_pond_overview': get_pond_overview,
    'get_stocking_data': get_stocking_data,
    'get_water_quality': get_water_quality,
    'get_feed_history': get_feed_history,
    'get_anco_history': get_anco_history,
    'get_sampling_history': get_sampling_history,
    'get_siphon_history': get_siphon_history,
    'get_treatment_history': get_treatment_history,
    'get_harvest_history': get_harvest_history,
    'get_production_summary': get_production_summary,
    'get_financial_summary': get_financial_summary,
    'get_receivables_payables': get_receivables_payables,
}


def _tool(name, description, properties, required=None):
    return {'type': 'function', 'function': {
        'name': name, 'description': description,
        'parameters': {'type': 'object', 'properties': properties, 'required': required or [], 'additionalProperties': False}
    }}


def tool_definitions():
    pond = {'type': ['integer', 'null'], 'description': 'ID kolam. Jika null gunakan kolam yang sedang dipilih di chat.'}
    cycle = {'type': ['integer', 'null'], 'description': 'ID siklus. Jika null gunakan siklus aktif/terpilih.'}
    days = {'type': 'integer', 'minimum': 1, 'maximum': 365, 'default': 30}
    return [
        _tool('get_active_cycle', 'Ambil informasi siklus budidaya aktif.', {'cycle_id': cycle}),
        _tool('get_pond_overview', 'Ringkasan semua kolam atau satu kolam dalam siklus.', {'cycle_id': cycle, 'pond_id': pond}),
        _tool('get_stocking_data', 'Ambil data tebar benur pada siklus.', {'cycle_id': cycle, 'pond_id': pond}),
        _tool('get_water_quality', 'Ambil histori DO, pH, suhu, salinitas dan parameter air.', {'cycle_id': cycle, 'pond_id': pond, 'days': days}),
        _tool('get_feed_history', 'Ambil histori pakan. Prioritas sumber adalah AncoCheck.daily_feed_kg (P/H), lalu FeedLog, lalu DailyPondRecord.', {'cycle_id': cycle, 'pond_id': pond, 'days': {'type': 'integer', 'minimum': 1, 'maximum': 365, 'default': 30}}),
        _tool('get_anco_history', 'Ambil histori cek anco pagi/siang/sore, status nafsu makan dan rekomendasi.', {'cycle_id': cycle, 'pond_id': pond, 'days': {'type': 'integer', 'minimum': 1, 'maximum': 180, 'default': 14}}),
        _tool('get_sampling_history', 'Ambil histori sampling ABW, size, ADG, FCR, SR, populasi dan biomassa.', {'cycle_id': cycle, 'pond_id': pond, 'days': {'type': 'integer', 'minimum': 1, 'maximum': 730, 'default': 90}}),
        _tool('get_siphon_history', 'Ambil histori siphon dan mortalitas.', {'cycle_id': cycle, 'pond_id': pond, 'days': {'type': 'integer', 'minimum': 1, 'maximum': 365, 'default': 30}}),
        _tool('get_treatment_history', 'Ambil histori treatment, dosis dan catatan.', {'cycle_id': cycle, 'pond_id': pond, 'days': {'type': 'integer', 'minimum': 1, 'maximum': 730, 'default': 90}}),
        _tool('get_harvest_history', 'Ambil histori panen parsial/total dan total kg.', {'cycle_id': cycle, 'pond_id': pond, 'days': {'type': 'integer', 'minimum': 1, 'maximum': 1825, 'default': 365}}),
        _tool('get_production_summary', 'Ringkasan produksi siklus: tebar, pakan, panen, mortalitas dan sampling terakhir.', {'cycle_id': cycle, 'pond_id': pond}),
        _tool('get_financial_summary', 'Ringkasan penjualan, pendapatan lain, biaya operasional dan laba sebelum penyesuaian lain.', {'cycle_id': cycle, 'date_from': {'type': ['string', 'null'], 'description': 'YYYY-MM-DD'}, 'date_to': {'type': ['string', 'null'], 'description': 'YYYY-MM-DD'}}),
        _tool('get_receivables_payables', 'Saldo piutang dan utang yang masih outstanding.', {'cycle_id': cycle}),
    ]


def execute_tool(name, arguments, *, current_cycle_id=None, current_pond_id=None):
    if name not in TOOLS:
        return {'status': 'error', 'message': 'Tool tidak diizinkan.'}
    args = dict(arguments or {})
    # The model may omit these. It cannot override the current cycle/pond with
    # arbitrary values when the UI has a selected scope.
    # UI-selected scope is authoritative. The model cannot escape it by
    # supplying another cycle/pond ID. When no scope is selected, the tool may
    # use the active cycle and all ponds.
    if current_cycle_id is not None:
        args['cycle_id'] = current_cycle_id
    elif args.get('cycle_id') is None:
        args['cycle_id'] = None
    if current_pond_id is not None and 'pond_id' in args:
        args['pond_id'] = current_pond_id
    try:
        return TOOLS[name](**args)
    except Exception as exc:
        return {'status': 'error', 'tool': name, 'message': f'Gagal membaca data aplikasi: {exc.__class__.__name__}: {exc}'}
