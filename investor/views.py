from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from django.shortcuts import render
from django.db.models import Sum
from operations.models import Harvest
from sales.models import Sale
from finance.models import OperationalExpense
from cultivation.utils import filter_selected_cycle


@login_required
@permission_required('investor.dashboard')
def dashboard(request):
    return render(request, 'investor/dashboard.html', {
        'modal_investor': 2000000000,
        'harvest_kg': filter_selected_cycle(request, Harvest.objects.all()).aggregate(s=Sum('total_kg'))['s'] or 0,
        'sales_total': filter_selected_cycle(request, Sale.objects.all()).aggregate(s=Sum('total_amount'))['s'] or 0,
        'expense_total': filter_selected_cycle(request, OperationalExpense.objects.all()).aggregate(s=Sum('amount'))['s'] or 0,
    })
