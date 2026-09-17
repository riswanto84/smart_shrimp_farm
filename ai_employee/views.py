import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from accounts.rbac import permission_required, has_permission
from .models import AIAction, EmployeeAdvance
from .services.operational_expense import create_expense_draft, execute_operational_expense, normalize_result, _file_payload, _vision_or_text
from cultivation.utils import get_selected_cycle
from .services.agent import interpret_command, execute_advance, rupiah

@permission_required('ai.finance')
def dashboard(request):
    pending = AIAction.objects.filter(status='draft').select_related('user').order_by('-created_at')[:20]
    advances = EmployeeAdvance.objects.select_related('employee').exclude(status='cancelled')[:20]
    return render(request, 'ai_employee/dashboard.html', {'pending': pending, 'advances': advances})

@login_required
@require_POST
def chat(request):
    if not (has_permission(request.user, 'ai.finance') or has_permission(request.user, 'ai.payroll')):
        return JsonResponse({'ok': False, 'message': 'Akses AI Employee ditolak.'}, status=403)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = request.POST
    command = str(payload.get('message', '')).strip()
    if not command:
        return JsonResponse({'ok': False, 'message': 'Perintah kosong.'}, status=400)
    result = interpret_command(request.user, command, request)
    return JsonResponse(result)

@permission_required('finance.expenses')
def operational_expense(request):
    if not has_permission(request.user, 'ai.finance'):
        messages.error(request, 'Akses AI OperationalExpense ditolak.')
        return render(request, 'accounts/forbidden.html', status=403)
    cycle = get_selected_cycle(request)
    if request.method == 'POST':
        uploaded = request.FILES.get('evidence')
        command = (request.POST.get('command') or '').strip()
        if not uploaded:
            messages.error(request, 'Lampirkan bukti pengeluaran terlebih dahulu.')
        elif not cycle:
            messages.error(request, 'Buat atau pilih Siklus Budidaya terlebih dahulu.')
        else:
            try:
                ext, data = _file_payload(uploaded)
                raw = _vision_or_text(data, ext, {'cycle_name': cycle.name}, command)
                extracted = normalize_result(raw, command, cycle)
                from django.core.files.uploadedfile import SimpleUploadedFile
                uploaded = SimpleUploadedFile(uploaded.name, data, content_type=getattr(uploaded, 'content_type', '') or None)
                action = create_expense_draft(request.user, command, extracted, uploaded, cycle, request)
                return render(request, 'ai_employee/operational_expense.html', {
                    'cycle': cycle, 'draft': action, 'extracted': extracted,
                    'document': action.expense_documents.first(), 'submitted': True,
                })
            except Exception as exc:
                messages.error(request, f'AI gagal menganalisis bukti: {exc}')
    return render(request, 'ai_employee/operational_expense.html', {'cycle': cycle, 'submitted': False})


@permission_required('ai.finance')
def operational_expense_edit(request, pk):
    """Review and complete an AI OperationalExpense draft before posting."""
    action = get_object_or_404(AIAction, pk=pk, action='operational_expense.create')
    if action.status != 'draft':
        messages.error(request, 'Draft ini sudah tidak dapat diedit.')
        return redirect('ai_employee:operational_expense')
    payload = dict(action.payload or {})
    cycle = get_selected_cycle(request)
    if payload.get('cycle_id'):
        from cultivation.models import CultivationCycle
        cycle = CultivationCycle.objects.filter(pk=payload.get('cycle_id')).first() or cycle
    from finance.models import OperationalExpense
    from ponds.models import Pond
    categories = OperationalExpense.CATEGORIES
    payment_methods = ['Cash', 'Transfer', 'QRIS', 'Tempo']
    ponds = Pond.objects.all().order_by('name')

    if request.method == 'POST':
        from .services.operational_expense import normalize_manual_result
        updated = normalize_manual_result(request.POST, cycle, payload)
        action.payload = updated
        action.result = {**(action.result or {}), 'extracted': updated}
        action.save(update_fields=['payload', 'result', 'updated_at'])
        from .services.audit import record_ai_event
        record_ai_event(
            action,
            request.user,
            'draft_edited',
            {'missing_fields': updated.get('missing_fields', [])},
            request,
        )

        # A single Save action is the final persistence step for
        # AI OperationalExpense. Once the user has completed the required
        # fields, create the real finance transaction immediately and return
        # to the Operational Expense list. If fields are still missing, keep
        # the user on this review page so nothing incomplete is posted.
        if not updated.get('missing_fields'):
            try:
                with transaction.atomic():
                    expense = execute_operational_expense(action, request.user, request)
                warning = ''
                doc_errors = (action.result or {}).get('document_errors') or []
                if doc_errors:
                    warning = ' Bukti tersimpan di draft AI, tetapi salinan ke dokumen keuangan gagal: ' + '; '.join(doc_errors)
                messages.success(
                    request,
                    f'Pengeluaran {expense.name} sebesar {rupiah(expense.amount)} berhasil disimpan ke Pengeluaran Operasional.{warning}',
                )
                return redirect('finance:expenses')
            except Exception as exc:
                messages.error(request, f'Pengeluaran belum dapat disimpan: {exc}')
        else:
            messages.warning(
                request,
                'Data draft disimpan, tetapi belum menjadi transaksi karena masih ada field wajib yang kosong.',
            )
        payload = updated

    document = action.expense_documents.first()
    return render(request, 'ai_employee/operational_expense_edit.html', {
        'action': action, 'extracted': payload, 'document': document,
        'cycle': cycle, 'categories': categories, 'payment_methods': payment_methods,
        'ponds': ponds,
    })


@permission_required('ai.approve')
@require_POST
def approve(request, pk):
    action = get_object_or_404(AIAction, pk=pk)
    if action.status != 'draft':
        messages.error(request, 'Action sudah diproses.')
        return redirect('ai_employee:dashboard')
    try:
        with transaction.atomic():
            if action.action == 'employee_advance.create':
                advance = execute_advance(action, request.user, request)
                messages.success(request, f'Kasbon {advance.employee.name} sebesar {rupiah(advance.amount)} berhasil diposting.')
            elif action.action == 'operational_expense.create':
                expense = execute_operational_expense(action, request.user, request)
                messages.success(request, f'Pengeluaran {expense.name} sebesar {rupiah(expense.amount)} berhasil diposting.')
            else:
                raise ValueError('Jenis action ini belum didukung untuk approval.')
    except Exception as exc:
        action.status = 'failed'
        action.result = {'error': str(exc)}
        action.save(update_fields=['status', 'result', 'updated_at'])
        messages.error(request, f'Gagal memproses action: {exc}')
    return redirect('finance:expenses')

@permission_required('ai.approve')
@require_POST
def reject(request, pk):
    action = get_object_or_404(AIAction, pk=pk)
    if action.status == 'draft':
        action.status = 'rejected'
        action.approved_by = request.user
        action.save(update_fields=['status', 'approved_by', 'updated_at'])
        from .services.audit import record_ai_event
        record_ai_event(action, request.user, 'rejected', {}, request)
        messages.success(request, 'Draft AI ditolak.')
    return redirect('finance:expenses')
