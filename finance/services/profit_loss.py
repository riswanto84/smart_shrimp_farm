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
    - Expense = every non-capital ``OperationalExpense`` record, including
      payroll and the posted ``Penyusutan`` category.
    - Fixed-asset accumulated depreciation remains a balance-sheet calculation;
      it is not added again here because doing so would double count expense.
    """
    sales = _filter_cycle(Sale.objects.all(), cycle).exclude(
        status__in=INVALID_SALE_STATUSES
    )
    expenses = _filter_cycle(
        OperationalExpense.objects.filter(is_capital_expenditure=False), cycle
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
    expense_total = expenses.aggregate(total=Sum('amount'))['total'] or ZERO

    grouped = list(
        expenses.values('category').annotate(total=Sum('amount')).order_by('category')
    )
    category_totals = {
        row['category']: row['total'] or ZERO
        for row in grouped
    }

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
        # Kept for template/backward compatibility. Depreciation is already
        # included when posted as OperationalExpense category "Penyusutan".
        'depreciation_total': category_totals.get('Penyusutan', ZERO),
        'expense_total': expense_total,
        'profit': profit,
    }
