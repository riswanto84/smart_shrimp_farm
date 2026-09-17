"""Sumber tunggal perhitungan biomassa Index.

Dashboard dan Neraca wajib memakai fungsi pada modul ini supaya angka biomassa
selalu sama. Dasar perhitungan adalah population_index / biomass_index dari
sampling terbaru, diproyeksikan dengan ADG sampai tanggal laporan, kemudian
dikurangi populasi panen parsial dan mortalitas siphon setelah sampling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable

from django.db.models import Sum
from django.utils import timezone

from cultivation.models import CultivationCycle
from operations.models import Harvest, SamplingRecord, SiphonRecord
from ponds.models import Pond

ZERO = Decimal("0")
THOUSAND = Decimal("1000")


def _d(value, default=ZERO) -> Decimal:
    try:
        if value in (None, ""):
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _is_total_harvest(value) -> bool:
    text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    return text in {"total", "final", "panen total", "panen final", "selesai"}


def _size(value) -> Decimal:
    match = re.search(r"\d+(?:[.,]\d+)?", str(value or ""))
    return _d(match.group(0).replace(",", ".")) if match else ZERO


def _cycle_completed(cycle, as_of: date) -> bool:
    """Tentukan apakah SIKLUS benar-benar sudah ditutup.

    Jangan memakai ``actual_end_date`` sebagai satu-satunya tanda selesai.
    Field tersebut pada data lama dapat terisi saat panen/penutupan operasional
    sebagian kolam, sementara siklus masih memiliki kolam dengan biomassa sisa.
    Untuk estimasi Nilai Sisa Udang, hanya status siklus yang eksplisit
    ``completed/selesai/closed`` yang boleh mengosongkan seluruh snapshot.
    ``as_of`` dipertahankan untuk kompatibilitas signature.
    """
    if not cycle:
        return False
    completed_value = getattr(cycle, "STATUS_COMPLETED", "completed")
    status = str(getattr(cycle, "status", "") or "").strip().lower()
    return status in {str(completed_value).lower(), "completed", "selesai", "closed"}


@dataclass(frozen=True)
class IndexBiomassResult:
    pond: Pond
    sampling: SamplingRecord
    cycle: CultivationCycle | None
    as_of: date
    sampling_age_days: int
    sampling_abw_g: Decimal
    adg_g_per_day: Decimal
    projected_abw_g: Decimal
    population_index_sampling: int
    harvested_population: int
    mortality_population: int
    remaining_population_index: int
    sampling_biomass_index_kg: Decimal
    growth_index_kg: Decimal
    partial_harvest_kg: Decimal
    mortality_index_kg: Decimal
    biomass_index_kg: Decimal
    excluded: bool = False
    exclusion_reason: str = ""

    @property
    def size(self) -> Decimal:
        return THOUSAND / self.projected_abw_g if self.projected_abw_g > 0 else ZERO


def calculate_pond_index_biomass(
    pond: Pond, as_of: date | None = None, cycle: CultivationCycle | None = None
) -> IndexBiomassResult | None:
    """Hitung biomassa Index aktual satu kolam pada tanggal tertentu."""
    as_of = as_of or timezone.localdate()
    sampling_qs = SamplingRecord.objects.filter(pond=pond, date__lte=as_of).select_related("cycle")
    # Jika dashboard sedang menampilkan satu siklus tertentu, JANGAN mengambil
    # sampling terbaru dari siklus lain. Ini sebelumnya menyebabkan biomassa
    # menjadi 0 ketika sampling siklus aktif berbeda dengan sampling terakhir
    # yang tersimpan pada kolam.
    if cycle is not None:
        sampling_qs = sampling_qs.filter(cycle=cycle)
    sampling = sampling_qs.order_by("-date", "-id").first()
    if not sampling:
        return None

    cycle = sampling.cycle
    pond_status = str(getattr(pond, "status", "") or "").strip().lower()
    operational = pond_status in {"budidaya", "panen", "active", "aktif"}

    harvests = Harvest.objects.filter(pond=pond, date__lte=as_of)
    if cycle:
        harvests = harvests.filter(cycle=cycle)
    else:
        harvests = harvests.filter(date__gte=sampling.date)
    harvest_rows = list(harvests.order_by("date", "id"))
    total_harvest = next((row for row in harvest_rows if _is_total_harvest(row.harvest_type)), None)

    exclusion_reason = ""
    if total_harvest:
        exclusion_reason = "Panen total"
    elif _cycle_completed(cycle, as_of):
        exclusion_reason = "Siklus selesai"
    elif not operational:
        exclusion_reason = "Kolam tidak aktif"

    sampling_abw = _d(sampling.abw_g)
    sampling_age = max((as_of - sampling.date).days, 0)
    target_adg = _d(getattr(cycle, "target_adg", None), Decimal("0.25"))
    adg = _d(sampling.adg_weekly or sampling.adg_cumulative or target_adg)
    if not (ZERO < adg <= Decimal("0.60")):
        adg = target_adg if ZERO < target_adg <= Decimal("0.60") else Decimal("0.25")
    projected_abw = sampling_abw + adg * Decimal(sampling_age)

    raw_index = _d(sampling.biomass_index_kg)
    population_index = int(getattr(sampling, "population_index", 0) or 0)
    if population_index <= 0 and raw_index > 0 and sampling_abw > 0:
        population_index = int((raw_index * THOUSAND / sampling_abw).quantize(Decimal("1")))

    harvested_population = 0
    partial_harvest_kg = ZERO
    for row in harvest_rows:
        if row.date <= sampling.date or _is_total_harvest(row.harvest_type):
            continue
        kg = _d(row.total_kg)
        partial_harvest_kg += kg
        harvest_size = _size(row.size_text)
        if harvest_size <= 0:
            elapsed = max((row.date - sampling.date).days, 0)
            harvest_abw = sampling_abw + adg * Decimal(elapsed)
            harvest_size = THOUSAND / harvest_abw if harvest_abw > 0 else ZERO
        if kg > 0 and harvest_size > 0:
            harvested_population += int((kg * harvest_size).quantize(Decimal("1")))

    siphons = SiphonRecord.objects.filter(pond=pond, date__gt=sampling.date, date__lte=as_of)
    if cycle:
        siphons = siphons.filter(cycle=cycle)
    mortality_population = int(siphons.aggregate(total=Sum("dead_count"))["total"] or 0)

    remaining_population = max(population_index - harvested_population - mortality_population, 0)
    projected_before_deductions = (
        Decimal(population_index) * projected_abw / THOUSAND
        if population_index > 0 and projected_abw > 0
        else raw_index
    )
    biomass_index = (
        Decimal(remaining_population) * projected_abw / THOUSAND
        if remaining_population > 0 and projected_abw > 0
        else ZERO
    )
    growth = max(projected_before_deductions - raw_index, ZERO)
    mortality_kg = Decimal(mortality_population) * projected_abw / THOUSAND if projected_abw > 0 else ZERO

    if exclusion_reason:
        biomass_index = ZERO

    return IndexBiomassResult(
        pond=pond,
        sampling=sampling,
        cycle=cycle,
        as_of=as_of,
        sampling_age_days=sampling_age,
        sampling_abw_g=sampling_abw,
        adg_g_per_day=adg,
        projected_abw_g=projected_abw,
        population_index_sampling=population_index,
        harvested_population=harvested_population,
        mortality_population=mortality_population,
        remaining_population_index=remaining_population,
        sampling_biomass_index_kg=raw_index,
        growth_index_kg=growth,
        partial_harvest_kg=partial_harvest_kg,
        mortality_index_kg=mortality_kg,
        biomass_index_kg=biomass_index.quantize(Decimal("0.01")),
        excluded=bool(exclusion_reason),
        exclusion_reason=exclusion_reason,
    )


def calculate_index_biomass_snapshot(
    *, as_of: date | None = None, ponds: Iterable[Pond] | None = None,
    cycle: CultivationCycle | None = None
) -> dict:
    """Hitung snapshot biomassa Index seluruh kolam aktif.

    Return shape stabil untuk dipakai Dashboard, Neraca, PDF, dan modul lain.
    """
    as_of = as_of or timezone.localdate()
    ponds = ponds if ponds is not None else Pond.objects.all().order_by("code", "name")
    rows: list[IndexBiomassResult] = []
    excluded: list[IndexBiomassResult] = []
    total = ZERO
    for pond in ponds:
        result = calculate_pond_index_biomass(pond, as_of, cycle=cycle)
        if result is None:
            continue
        if result.excluded:
            excluded.append(result)
            continue
        rows.append(result)
        total += result.biomass_index_kg
    return {
        "as_of": as_of,
        "method": "INDEX",
        "cycle_id": cycle.id if cycle is not None else None,
        "rows": rows,
        "by_pond": {row.pond.id: row for row in rows},
        "excluded": excluded,
        "total_kg": total.quantize(Decimal("0.01")),
        "total_ton": (total / THOUSAND).quantize(Decimal("0.01")),
    }
