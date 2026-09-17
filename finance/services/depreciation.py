"""Authoritative straight-line depreciation engine.

All financial modules must use this service so Dashboard, profit/loss, balance
sheet, depreciation report, PDF and cycle history never calculate depreciation
with different rules.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Optional

from django.utils import timezone

from finance.models import FixedAsset

ZERO = Decimal('0')
TWELVE = Decimal('12')


def fiscal_life_years(group: str) -> Optional[int]:
    return {
        'group_1': 4,
        'group_2': 8,
        'group_3': 16,
        'group_4': 20,
        'permanent_building': 20,
        'non_permanent_building': 10,
    }.get(group)


def months_used(asset: FixedAsset, as_of: date) -> int:
    if asset.use_date > as_of or asset.fiscal_group == 'non_depreciable':
        return 0
    months = (as_of.year - asset.use_date.year) * 12 + as_of.month - asset.use_date.month + 1
    life = fiscal_life_years(asset.fiscal_group)
    if life:
        months = min(months, life * 12)
    return max(months, 0)


def calculate_asset_depreciation(asset: FixedAsset, as_of: Optional[date] = None) -> dict:
    as_of = as_of or timezone.localdate()
    cost = asset.total_cost or ZERO
    life = fiscal_life_years(asset.fiscal_group)
    residual = asset.residual_value or ZERO

    if not life or asset.fiscal_group == 'non_depreciable':
        annual = ZERO
        accumulated = ZERO
    else:
        depreciable = max(cost - residual, ZERO)
        annual = depreciable / Decimal(life)
        accumulated = min((annual / TWELVE) * Decimal(months_used(asset, as_of)), depreciable)

    return {
        'annual': annual,
        'accumulated': accumulated,
        'book_value': max(cost - accumulated, ZERO),
        'life': life,
    }


def calculate_depreciation_summary(
    *,
    as_of: Optional[date] = None,
    period_start: Optional[date] = None,
    assets: Optional[Iterable[FixedAsset]] = None,
) -> dict:
    """Return one canonical depreciation summary.

    ``period_depreciation`` is the movement in accumulated depreciation between
    the day before ``period_start`` and ``as_of``. When ``period_start`` is not
    supplied, it defaults to 1 January of ``as_of`` (year-to-date).
    """
    as_of = as_of or timezone.localdate()
    if period_start is None:
        period_start = date(as_of.year, 1, 1)
    if period_start > as_of:
        period_start = as_of

    queryset = assets if assets is not None else FixedAsset.objects.exclude(status='disposed')
    rows = []
    total_cost = ZERO
    total_period = ZERO
    total_accumulated = ZERO
    total_book = ZERO
    before_date = period_start - timedelta(days=1)

    for asset in queryset:
        current = calculate_asset_depreciation(asset, as_of)
        before = calculate_asset_depreciation(asset, before_date)['accumulated']
        period_value = max(current['accumulated'] - before, ZERO)
        rows.append({'asset': asset, **current, 'current_year': period_value, 'period_depreciation': period_value})
        total_cost += asset.total_cost or ZERO
        total_period += period_value
        total_accumulated += current['accumulated']
        total_book += current['book_value']

    return {
        'as_of': as_of,
        'period_start': period_start,
        'rows': rows,
        'asset_count': len(rows),
        'total_cost': total_cost,
        'period_depreciation': total_period,
        'current_year_depreciation': total_period,
        'accumulated_depreciation': total_accumulated,
        'book_value': total_book,
    }
