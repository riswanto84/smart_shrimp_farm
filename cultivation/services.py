from decimal import Decimal
from django.db import models
from django.db.models import Sum, Avg
from django.utils import timezone


def build_cycle_final_snapshot(cycle):
    """Buat snapshot KPI akhir agar nilai arsip tidak berubah di kemudian hari."""
    from operations.models import SamplingRecord, Harvest, DailyPondRecord, SiphonRecord

    samples = SamplingRecord.objects.filter(cycle=cycle)
    latest_date = samples.order_by('-date').values_list('date', flat=True).first()
    latest = samples.filter(date=latest_date) if latest_date else samples.none()

    harvest_total = Harvest.objects.filter(cycle=cycle).aggregate(v=Sum('total_kg'))['v'] or Decimal('0')
    feed_total = DailyPondRecord.objects.filter(cycle=cycle).aggregate(v=Sum('daily_feed_kg'))['v'] or Decimal('0')
    mortality_total = SiphonRecord.objects.filter(cycle=cycle).aggregate(v=Sum('dead_count'))['v'] or 0

    return {
        'generated_at': timezone.now().isoformat(),
        'latest_sampling_date': latest_date.isoformat() if latest_date else None,
        'pond_count': latest.values('pond_id').distinct().count(),
        'average_abw_g': float(latest.aggregate(v=Avg('abw_g'))['v'] or 0),
        'average_adg': float(latest.aggregate(v=Avg('adg_weekly'))['v'] or 0),
        'average_fcr': float(latest.aggregate(v=Avg('fcr'))['v'] or 0),
        'biomass_fr_kg': float(latest.aggregate(v=Sum('biomass_kg'))['v'] or 0),
        'harvest_total_kg': float(harvest_total),
        'feed_total_kg': float(feed_total),
        'mortality_total': int(mortality_total),
    }



def build_cycle_history_metrics(cycle):
    """Ringkasan lengkap satu siklus untuk halaman arsip dan perbandingan."""
    from collections import defaultdict
    from django.db.models import Sum, Avg, Count
    from operations.models import (
        Stocking, SamplingRecord, Harvest, DailyPondRecord,
        SiphonRecord, AncoCheck, DailyParameter,
    )
    from finance.services.profit_loss import calculate_profit_loss

    zero = Decimal('0')
    profit = calculate_profit_loss(cycle=cycle)
    harvest_qs = Harvest.objects.filter(cycle=cycle).select_related('pond')
    stocking_qs = Stocking.objects.filter(cycle=cycle).select_related('pond')
    samples = SamplingRecord.objects.filter(cycle=cycle).select_related('pond')
    latest_date = samples.order_by('-date', '-id').values_list('date', flat=True).first()

    latest_by_pond = {}
    if latest_date:
        for sample in samples.filter(date=latest_date).order_by('pond__name', '-id'):
            latest_by_pond.setdefault(sample.pond_id, sample)

    harvest_by_pond = {
        row['pond_id']: row for row in harvest_qs.values('pond_id', 'pond__name').annotate(
            total_kg=Sum('total_kg'), harvest_count=Count('id'), last_date=models.Max('date')
        )
    }
    stocking_by_pond = {
        row['pond_id']: row for row in stocking_qs.values('pond_id', 'pond__name').annotate(
            seed_count=Sum('seed_count')
        )
    }

    pond_ids = set(latest_by_pond) | set(harvest_by_pond) | set(stocking_by_pond)
    pond_rows = []
    for pond_id in sorted(pond_ids, key=lambda x: (
        (latest_by_pond.get(x).pond.name if x in latest_by_pond else
         harvest_by_pond.get(x, stocking_by_pond.get(x, {})).get('pond__name', ''))
    )):
        sample = latest_by_pond.get(pond_id)
        harvest = harvest_by_pond.get(pond_id, {})
        stocking = stocking_by_pond.get(pond_id, {})
        seed_count = int(stocking.get('seed_count') or 0)
        harvested = harvest.get('total_kg') or zero
        abw = getattr(sample, 'abw_g', None) or zero
        fcr = getattr(sample, 'fcr', None) or zero
        adg = getattr(sample, 'adg_weekly', None) or zero
        sr_index = getattr(sample, 'sr_index', None)
        if sr_index is None:
            sr_index = getattr(sample, 'estimated_sr', None) or zero
        pond_rows.append({
            'pond_id': pond_id,
            'pond_name': sample.pond.name if sample else harvest.get('pond__name') or stocking.get('pond__name') or '-',
            'seed_count': seed_count,
            'harvest_total_kg': harvested,
            'harvest_count': harvest.get('harvest_count') or 0,
            'last_harvest_date': harvest.get('last_date'),
            'abw_g': abw,
            'size': getattr(sample, 'size', None) or zero,
            'adg': adg,
            'fcr': fcr,
            'sr_index': sr_index,
            'biomass_fr_kg': getattr(sample, 'biomass_kg', None) or zero,
            'biomass_index_kg': getattr(sample, 'biomass_index_kg', None) or zero,
        })

    total_stocking = stocking_qs.aggregate(v=Sum('seed_count'))['v'] or 0
    total_harvest = harvest_qs.aggregate(v=Sum('total_kg'))['v'] or zero
    total_feed = DailyPondRecord.objects.filter(cycle=cycle).aggregate(v=Sum('daily_feed_kg'))['v'] or zero
    mortality = SiphonRecord.objects.filter(cycle=cycle).aggregate(v=Sum('dead_count'))['v'] or 0
    valid_samples = [r for r in pond_rows if r['abw_g']]
    avg_fcr = (sum((Decimal(str(r['fcr'])) for r in valid_samples), zero) / len(valid_samples)) if valid_samples else zero
    avg_adg = (sum((Decimal(str(r['adg'])) for r in valid_samples), zero) / len(valid_samples)) if valid_samples else zero
    avg_sr = (sum((Decimal(str(r['sr_index'])) for r in valid_samples), zero) / len(valid_samples)) if valid_samples else zero
    avg_abw = (sum((Decimal(str(r['abw_g'])) for r in valid_samples), zero) / len(valid_samples)) if valid_samples else zero
    avg_price = (profit['sales_revenue'] / total_harvest) if total_harvest else zero
    roi = (profit['profit'] / profit['expense_total'] * 100) if profit['expense_total'] else zero

    return {
        'cycle': cycle,
        'period_end': cycle.actual_end_date or cycle.target_end_date,
        'duration_days': ((cycle.actual_end_date or timezone.localdate()) - cycle.start_date).days + 1 if cycle.start_date else 0,
        'total_stocking': total_stocking,
        'total_harvest_kg': total_harvest,
        'total_feed_kg': total_feed,
        'mortality_total': mortality,
        'average_abw_g': avg_abw,
        'average_adg': avg_adg,
        'average_fcr': avg_fcr,
        'average_sr_index': avg_sr,
        'average_price_per_kg': avg_price,
        'revenue': profit['revenue'],
        'expense': profit['expense_total'],
        'profit': profit['profit'],
        'roi_percent': roi,
        'pond_rows': pond_rows,
        'sampling_count': samples.count(),
        'harvest_count': harvest_qs.count(),
        'anco_count': AncoCheck.objects.filter(cycle=cycle).count(),
        'parameter_count': DailyParameter.objects.filter(cycle=cycle).count(),
        'siphon_count': SiphonRecord.objects.filter(cycle=cycle).count(),
        'latest_sampling_date': latest_date,
        'expense_categories': profit['grouped'],
    }
