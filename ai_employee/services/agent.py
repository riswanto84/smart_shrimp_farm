import json
import re
from decimal import Decimal, InvalidOperation
from datetime import date
from django.db.models import Sum
from payroll.models import Employee, PayrollRecord
from .audit import record_ai_event
from ..models import AIAction, EmployeeAdvance
from chat_ai.services import ask_ollama


def rupiah(v):
    return 'Rp{:,.0f}'.format(Decimal(v or 0)).replace(',', '.')


def parse_money(text):
    s = text.lower().replace('rp', '').replace(' ', '')
    m = re.search(r'(\d[\d\.,]*)\s*(juta|jt|ribu|rb|m)?', s)
    if not m:
        return None
    raw, unit = m.group(1), (m.group(2) or '')
    if unit in ('juta', 'jt'):
        return Decimal(raw.replace('.', '').replace(',', '.')) * 1_000_000
    if unit in ('ribu', 'rb'):
        return Decimal(raw.replace('.', '').replace(',', '.')) * 1_000
    # Indonesian shorthand: 500.000 / 500,000
    try:
        if raw.count('.') > 1 or ('.' in raw and len(raw.rsplit('.', 1)[1]) == 3):
            return Decimal(raw.replace('.', '').replace(',', ''))
        if raw.count(',') > 1 or (',' in raw and len(raw.rsplit(',', 1)[1]) == 3):
            return Decimal(raw.replace(',', ''))
        return Decimal(raw.replace(',', '.'))
    except InvalidOperation:
        return None


def find_employee(text):
    words = re.findall(r'[A-Za-zÀ-ÿ0-9_-]{3,}', text)
    qs = Employee.objects.filter(employment_status='active')
    for word in words:
        matches = qs.filter(name__icontains=word) | qs.filter(employee_code__icontains=word)
        if matches.exists():
            return matches.order_by('name').first()
    return None


def advance_balance(employee):
    return EmployeeAdvance.objects.filter(employee=employee).exclude(status='cancelled').aggregate(
        total=Sum('amount'), repaid=Sum('repaid_amount')
    )


def create_advance_draft(user, command, employee, amount, purpose, request=None):
    payload = {
        'employee_id': employee.id,
        'employee_name': employee.name,
        'amount': str(amount),
        'purpose': purpose,
        'advance_date': date.today().isoformat(),
    }
    action = AIAction.objects.create(user=user, action='employee_advance.create', command=command, payload=payload, status='draft')
    record_ai_event(action, user, 'draft_created', {'amount': str(amount), 'employee_id': employee.id}, request)
    return action


def execute_advance(action, approver, request=None):
    if action.status != 'draft':
        raise ValueError('Action ini sudah diproses.')
    p = action.payload
    employee = Employee.objects.get(pk=p['employee_id'], employment_status='active')
    amount = Decimal(p['amount'])
    advance = EmployeeAdvance.objects.create(
        employee=employee,
        advance_date=date.fromisoformat(p['advance_date']),
        amount=amount,
        purpose=p.get('purpose', ''),
        created_by=approver,
    )
    from django.utils import timezone
    action.status = 'executed'
    action.approved_by = approver
    action.approved_at = timezone.now()
    action.executed_at = timezone.now()
    action.result = {'advance_id': advance.id, 'employee': employee.name, 'amount': str(amount)}
    action.save(update_fields=['status', 'approved_by', 'approved_at', 'executed_at', 'result', 'updated_at'])
    record_ai_event(action, approver, 'executed', {'advance_id': advance.id, 'amount': str(amount)}, request)
    return advance


def interpret_command(user, command, request=None):
    text = command.strip()
    low = text.lower()

    # Deterministic financial commands are deliberately handled before the LLM.
    # Read-only kasbon queries must be checked before create commands.
    if 'sisa kasbon' in low or 'saldo kasbon' in low or ('kasbon' in low and any(k in low for k in ('berapa', 'cek', 'lihat'))):
        employee = find_employee(text)
        if not employee:
            return {'ok': False, 'message': 'Sebutkan nama atau kode pegawai yang ingin dicek.'}
        bal = advance_balance(employee)
        current = (bal.get('total') or Decimal('0')) - (bal.get('repaid') or Decimal('0'))
        action = AIAction.objects.create(user=user, action='employee.read', command=text, payload={'employee_id': employee.id}, result={'outstanding': str(current)}, status='executed')
        record_ai_event(action, user, 'read', {'employee_id': employee.id, 'outstanding': str(current)}, request)
        return {'ok': True, 'type': 'answer', 'message': f'Saldo kasbon {employee.name} saat ini {rupiah(current)}.'}

    if any(k in low for k in ('kasbon', 'pinjaman pegawai', 'uang muka pegawai')):
        employee = find_employee(text)
        amount = parse_money(text)
        if not employee:
            return {'ok': False, 'message': 'Saya belum menemukan nama/kode pegawai. Contoh: "Kasbon Budi Rp500.000".'}
        if not amount or amount <= 0:
            return {'ok': False, 'message': 'Nominal kasbon belum jelas. Contoh: "Kasbon Budi Rp500.000".'}
        purpose = ''
        m = re.search(r'(?:untuk|keperluan)\s+(.+)$', text, re.I)
        if m:
            purpose = m.group(1).strip()
        action = create_advance_draft(user, text, employee, amount, purpose, request)
        bal = advance_balance(employee)
        current = (bal.get('total') or Decimal('0')) - (bal.get('repaid') or Decimal('0'))
        return {
            'ok': True, 'type': 'draft', 'action_id': action.id,
            'message': f'Draft kasbon dibuat untuk {employee.name}: {rupiah(amount)}. Saldo kasbon saat ini {rupiah(current)}, setelah kasbon menjadi {rupiah(current + amount)}. Menunggu persetujuan.'
        }

    if 'gaji' in low or 'payroll' in low:
        employee = find_employee(text)
        if employee and any(k in low for k in ('berapa', 'lihat', 'cek')):
            record = PayrollRecord.objects.filter(employee=employee).select_related('period').order_by('-period__start_date', '-id').first()
            if not record:
                return {'ok': True, 'type': 'answer', 'message': f'Belum ada data payroll untuk {employee.name}.'}
            action = AIAction.objects.create(user=user, action='payroll.read', command=text, payload={'employee_id': employee.id}, result={'record_id': record.id, 'net_salary': str(record.net_salary)}, status='executed')
            record_ai_event(action, user, 'read', {'employee_id': employee.id, 'record_id': record.id}, request)
            return {'ok': True, 'type': 'answer', 'message': f'Payroll terakhir {employee.name}: {record.period.name}. Gaji bersih {rupiah(record.net_salary)}, dibayar {rupiah(record.amount_paid)}, status {record.get_payment_status_display()}.'}

    # Ask Ollama for informational queries; no write action is inferred from free-form LLM output.
    prompt = (
        'Anda adalah AI Employee Finance/Payroll Smart Shrimp Farm. Jawab singkat dalam bahasa Indonesia. '
        'Anda hanya boleh menjelaskan atau meminta klarifikasi; jangan mengklaim telah mengubah database.\n\n'
        f'Perintah pengguna: {text}'
    )
    answer = ask_ollama(prompt, timeout=90)
    return {'ok': True, 'type': 'answer', 'message': answer}
