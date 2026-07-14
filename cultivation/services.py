from decimal import Decimal
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
