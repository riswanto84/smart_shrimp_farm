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
from chat_ai.services import ollama_health
from cultivation.utils import filter_selected_cycle

def home(request):
    # Halaman company profile/public home dinonaktifkan.
    # Root aplikasi langsung diarahkan ke halaman login admin.
    return redirect('accounts:login')
@login_required
@permission_required('dashboard')
def dashboard(request):
    ponds=Pond.objects.all()
    sales_total=filter_selected_cycle(request, Sale.objects.all()).aggregate(s=Sum('total_amount'))['s'] or 0
    expense_total=filter_selected_cycle(request, OperationalExpense.objects.all()).aggregate(s=Sum('amount'))['s'] or 0
    latest=filter_selected_cycle(request, DailyParameter.objects.select_related('pond').order_by('-date','-created_at')).first()
    ollama_status = ollama_health(timeout=2)
    return render(request,'core/dashboard.html',{'ponds':ponds,'sales_total':sales_total,'expense_total':expense_total,'latest':latest,'ollama_status':ollama_status})


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


@login_required
@permission_required('dashboard')
def ollama_status_api(request):
    """Status Ollama aktual untuk refresh dashboard tanpa reload penuh."""
    return JsonResponse(ollama_health(timeout=2))
