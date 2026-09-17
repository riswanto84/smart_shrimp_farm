"""Central profit/loss calculation service.

Dashboard, profit/loss reports and balance sheet MUST use this module so the
operating result cannot drift because of different querysets or depreciation
rules.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Sum

from finance.models import OperationalExpense, OtherRevenue
from finance.services.depreciation import calculate_depreciation_summary
from sales.models import Sale

ZERO = Decimal('0')
INVALID_SALE_STATUSES = ('Gagal', 'Expired', 'Dibatalkan', 'Refund')


def _filter_cycle(queryset, cycle):
    if cycle is not None and hasattr(queryset.model, 'cycle_id'):
        return queryset.filter(cycle=cycle)
    return queryset


def calculate_profit_loss(
    *,
    cycle=None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict:
    """Return one authoritative operating profit/loss result.

    Accounting policy used by the application:
    - Revenue = valid sales + other revenue.
    - Operating expenses come from non-capital ``OperationalExpense`` records.
    - Posted rows in category ``Penyusutan`` are excluded to prevent duplicates.
    - Depreciation is calculated once from the fixed-asset register by the
      authoritative depreciation engine.
    """
    sales = _filter_cycle(Sale.objects.all(), cycle).exclude(
        status__in=INVALID_SALE_STATUSES
    )
    # Penyusutan tidak dibaca dari OperationalExpense karena data historis dapat
    # berisi posting otomatis/duplikat. Nilainya selalu dihitung oleh engine aset.
    expenses = _filter_cycle(
        OperationalExpense.objects.filter(is_capital_expenditure=False).exclude(category='Penyusutan'), cycle
    )
    other_revenue = OtherRevenue.objects.all()

    if date_from:
        sales = sales.filter(date__date__gte=date_from)
        expenses = expenses.filter(date__gte=date_from)
        other_revenue = other_revenue.filter(date__gte=date_from)
    if date_to:
        sales = sales.filter(date__date__lte=date_to)
        expenses = expenses.filter(date__lte=date_to)
        other_revenue = other_revenue.filter(date__lte=date_to)

    sales_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or ZERO
    other_revenue_total = (
        other_revenue.aggregate(total=Sum('gross_amount'))['total'] or ZERO
    )
    operating_expense_total = expenses.aggregate(total=Sum('amount'))['total'] or ZERO

    effective_date_to = date_to or date.today()
    depreciation_start = date_from or date(effective_date_to.year, 1, 1)
    depreciation_summary = calculate_depreciation_summary(
        as_of=effective_date_to,
        period_start=depreciation_start,
    )
    depreciation_total = depreciation_summary['period_depreciation']
    expense_total = operating_expense_total + depreciation_total

    grouped = list(
        expenses.values('category').annotate(total=Sum('amount')).order_by('category')
    )
    category_totals = {
        row['category']: row['total'] or ZERO
        for row in grouped
    }
    category_totals['Penyusutan'] = depreciation_total
    grouped = [row for row in grouped if row['category'] != 'Penyusutan']
    grouped.append({'category': 'Penyusutan', 'total': depreciation_total})
    grouped.sort(key=lambda row: row['category'])

    total_revenue = sales_revenue + other_revenue_total
    profit = total_revenue - expense_total

    return {
        'cycle': cycle,
        'date_from': date_from,
        'date_to': date_to,
        'sales_queryset': sales,
        'expense_queryset': expenses,
        'other_revenue_queryset': other_revenue,
        'sales_revenue': sales_revenue,
        'other_revenue': other_revenue_total,
        'revenue': total_revenue,
        'expenses': expenses,
        'grouped': grouped,
        'category_totals': category_totals,
        'operating_cost': expense_total,
        'operating_expense_before_depreciation': operating_expense_total,
        'depreciation_summary': depreciation_summary,
        # Kept for template/backward compatibility; value comes from the
        # authoritative fixed-asset depreciation engine.
        'depreciation_total': depreciation_total,
        'expense_total': expense_total,
        'profit': profit,
    }
