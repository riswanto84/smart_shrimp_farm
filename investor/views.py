from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from django.shortcuts import render
from django.db.models import Sum
from operations.models import Harvest
from sales.models import Sale
from finance.models import OperationalExpense


@login_required
@permission_required('investor.dashboard')
def dashboard(request):
    return render(request, 'investor/dashboard.html', {
        'modal_investor': 2000000000,
        'harvest_kg': Harvest.objects.aggregate(s=Sum('total_kg'))['s'] or 0,
        'sales_total': Sale.objects.aggregate(s=Sum('total_amount'))['s'] or 0,
        'expense_total': OperationalExpense.objects.aggregate(s=Sum('amount'))['s'] or 0,
    })
