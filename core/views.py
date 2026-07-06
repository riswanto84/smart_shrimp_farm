from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from ponds.models import Pond
from operations.models import DailyParameter
from sales.models import Sale
from finance.models import OperationalExpense
from django.db.models import Sum

def home(request):
    # Halaman company profile/public home dinonaktifkan.
    # Root aplikasi langsung diarahkan ke halaman login admin.
    return redirect('accounts:login')
@login_required
@permission_required('dashboard')
def dashboard(request):
    ponds=Pond.objects.all()
    sales_total=Sale.objects.aggregate(s=Sum('total_amount'))['s'] or 0
    expense_total=OperationalExpense.objects.aggregate(s=Sum('amount'))['s'] or 0
    latest=DailyParameter.objects.select_related('pond').order_by('-date','-created_at').first()
    return render(request,'core/dashboard.html',{'ponds':ponds,'sales_total':sales_total,'expense_total':expense_total,'latest':latest})


@login_required
@require_POST
@permission_required('dashboard')
def mark_notifications_read(request):
    """Tandai notifikasi aktif sebagai sudah dibaca untuk session user saat ini."""
    key = request.POST.get('key', '').strip()
    if key:
        request.session['ssf_notifications_read_key'] = key
        request.session.modified = True
    return JsonResponse({'ok': True})
