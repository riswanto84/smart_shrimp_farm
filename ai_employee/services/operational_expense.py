import base64
import json
import mimetypes
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from chat_ai.services import stream_ollama
from finance.models import OperationalExpense, ExpenseDocument
from ponds.models import Pond
from cultivation.models import CultivationCycle
from ..models import AIAction, AIOperationalExpenseDocument
from .audit import record_ai_event

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
PAYMENT_METHODS = {'Cash', 'Transfer', 'QRIS', 'Tempo'}

# Fallback semantic mapping: when the document does not explicitly state a
# category, infer it conservatively from the expense name/notes/instructions.
# The output is always restricted to OperationalExpense.CATEGORIES.
CATEGORY_KEYWORDS = {
    'Pakan': ('pakan', 'feed', 'pellet', 'pelet'),
    'Listrik': ('listrik', 'pln', 'token listrik', 'kwh', 'electric'),
    'BBM': ('bbm', 'solar', 'dexlite', 'pertalite', 'pertamax', 'bensin', 'diesel', 'fuel'),
    'Obat & Probiotik': ('obat', 'probiotik', 'probiotic', 'vitamin', 'mineral', 'disinfectant', 'disinfektan'),
    'Tenaga Kerja': ('gaji', 'upah', 'lembur', 'honor', 'pegawai', 'karyawan', 'kasbon'),
    'Jasa Pengelola': ('jasa pengelola', 'management fee', 'fee pengelola'),
    'Peralatan': ('peralatan', 'alat baru', 'mesin baru', 'genset baru', 'kincir baru', 'equipment'),
    'Perbaikan': ('perbaikan', 'servis', 'service', 'repair', 'sparepart', 'suku cadang', 'oli', 'gearbox', 'bearing', 'seal', 'maintenance'),
    'Transportasi': ('transport', 'angkutan', 'ongkir', 'pengiriman', 'ekspedisi', 'bensin perjalanan', 'tol'),
    'Panen': ('panen', 'harvest', 'jaring panen', 'es panen'),
    'Administrasi': ('atk', 'alat tulis', 'materai', 'administrasi', 'fotokopi', 'print', 'cetak', 'notaris'),
    'Penyusutan': ('penyusutan', 'depresiasi', 'depreciation'),
    'Pajak': ('pajak', 'pph', 'ppn', 'npwp', 'tax'),
    'Benur': ('benur', 'post larva', 'pl', 'nauplii'),
}


def _infer_category(text, current=''):
    """Infer a valid category from natural-language evidence without inventing it."""
    valid = dict(OperationalExpense.CATEGORIES)
    if current and current in valid:
        return current, False
    normalized = re.sub(r'\s+', ' ', (text or '').lower()).strip()
    if not normalized:
        return '', False
    # Prefer longer/more specific phrases first.
    matches = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category not in valid:
            continue
        for keyword in keywords:
            if keyword in normalized:
                matches.append((len(keyword), category))
    if not matches:
        return '', False
    matches.sort(reverse=True)
    return matches[0][1], True


def _decimal(value):
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        return value
    raw = str(value).strip().lower().replace('rp', '').replace(' ', '')
    raw = raw.replace('.', '').replace(',', '.')
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _extract_json(text):
    cleaned = (text or '').strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.I)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r'\{.*\}', cleaned, flags=re.S)
        if match:
            return json.loads(match.group(0))
    raise ValueError('AI tidak mengembalikan JSON yang valid.')


def _file_payload(uploaded_file):
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Format bukti yang dapat dianalisis AI: PDF, JPG, JPEG, PNG, atau WEBP.')
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValueError('Ukuran bukti maksimal 10 MB per file.')
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return ext, data


def _pdf_text(data):
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or '') for page in reader.pages[:8]]
        return '\n'.join(pages).strip()[:20000]
    except Exception:
        return ''


def _vision_or_text(data, ext, context, command):
    categories = [value for value, _ in OperationalExpense.CATEGORIES]
    ponds = list(Pond.objects.values('id', 'name').order_by('name'))
    pond_text = ', '.join(f"{p['id']}:{p['name']}" for p in ponds) or '(tidak ada data kolam)'
    extracted_text = _pdf_text(data) if ext == '.pdf' else ''
    schema = {
        'date': 'YYYY-MM-DD atau null',
        'category': categories,
        'name': 'nama pengeluaran yang singkat',
        'amount': 'angka desimal tanpa simbol rupiah atau null',
        'payment_method': list(PAYMENT_METHODS),
        'pond_id': 'ID kolam dari daftar atau null',
        'document_number': 'nomor invoice/nota/bukti jika ada, atau string kosong',
        'notes': 'catatan singkat dari bukti, atau string kosong',
        'confidence': {'date': 0, 'category': 0, 'name': 0, 'amount': 0, 'payment_method': 0, 'pond_id': 0, 'document_number': 0},
        'missing_fields': [],
    }
    prompt = f"""Anda adalah AI OperationalExpense untuk Smart Shrimp Farm.
Baca bukti pengeluaran dan instruksi pengguna lalu ekstrak data untuk FORM PENGELUARAN OPERASIONAL.
Jangan mengarang angka. Jika informasi tidak ada atau tidak yakin, gunakan null dan masukkan field tersebut ke missing_fields.
Tanggal harus tanggal transaksi pada bukti, bukan tanggal analisis, kecuali pengguna memberikan tanggal.
Nominal harus total pengeluaran/total tagihan jika tersedia, bukan subtotal.
Kategori WAJIB salah satu dari: {categories}
Metode pembayaran WAJIB salah satu dari: {list(PAYMENT_METHODS)} atau null.
Kolam hanya boleh memakai ID dari daftar: {pond_text}. Jika tidak diketahui, null.
Kembalikan HANYA JSON sesuai skema ini, tanpa markdown:
{json.dumps(schema, ensure_ascii=False)}

Siklus aktif: {context.get('cycle_name') or '-'}
Instruksi pengguna: {command or '(tidak ada)'}
Teks PDF (jika ada):
{extracted_text or '(tidak tersedia; jika gambar gunakan kemampuan vision)'}
"""
    images = [base64.b64encode(data).decode('ascii')] if ext in IMAGE_EXTENSIONS else None
    model = getattr(settings, 'OLLAMA_VISION_MODEL', None) or getattr(settings, 'OLLAMA_MODEL', 'gemma2:2b')
    messages = [
        {'role': 'system', 'content': 'Ekstrak bukti pengeluaran secara konservatif dan selalu keluarkan JSON valid.'},
        {'role': 'user', 'content': prompt},
    ]
    chunks = list(stream_ollama(messages, model=model, images=images, timeout=180))
    return _extract_json(''.join(chunks))


def normalize_result(raw, command, cycle):
    categories = dict(OperationalExpense.CATEGORIES)
    result = dict(raw or {})
    date_value = _parse_date(result.get('date'))
    amount = _decimal(result.get('amount'))
    category = str(result.get('category') or '').strip()
    category = next((v for v in categories if v.lower() == category.lower()), '')
    # If the model returned no usable category, use deterministic semantic
    # mapping from the extracted name/notes plus the user's instruction.
    inference_text = ' '.join([
        str(result.get('name') or ''),
        str(result.get('notes') or ''),
        str(command or ''),
    ])
    inferred_category, inferred = _infer_category(inference_text, category)
    if inferred_category:
        category = inferred_category
        if inferred and 'category' in (result.get('missing_fields') or []):
            # It is no longer missing after deterministic mapping.
            pass
    payment = str(result.get('payment_method') or '').strip()
    payment = next((v for v in PAYMENT_METHODS if v.lower() == payment.lower()), '')
    pond_id = result.get('pond_id')
    try:
        pond_id = int(pond_id) if pond_id not in (None, '') else None
    except (TypeError, ValueError):
        pond_id = None
    if pond_id is not None and not Pond.objects.filter(pk=pond_id).exists():
        pond_id = None
    # Recompute required-field status from normalized values instead of blindly
    # trusting the model's missing_fields list. This prevents stale AI flags
    # from blocking an otherwise complete draft.
    missing = []
    if not date_value and command:
        for text in re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b', command):
            date_value = _parse_date(text)
            if date_value:
                break
    values = {
        'date': date_value,
        'category': category,
        'name': str(result.get('name') or '').strip(),
        'amount': amount,
        'payment_method': payment,
    }
    for field, value in values.items():
        if value in (None, '', 0) and field not in missing:
            missing.append(field)
    return {
        'date': date_value.isoformat() if date_value else '',
        'category': category,
        'name': values['name'],
        'amount': str(amount or Decimal('0')),
        'payment_method': payment,
        'pond_id': pond_id,
        'document_number': str(result.get('document_number') or '').strip(),
        'notes': str(result.get('notes') or '').strip(),
        'confidence': result.get('confidence') if isinstance(result.get('confidence'), dict) else {},
        'category_source': 'semantic_fallback' if inferred else 'document_or_ai',
        'missing_fields': missing,
        'cycle_id': cycle.id if cycle else None,
        'cycle_name': cycle.name if cycle else '',
    }



def normalize_manual_result(data, cycle, existing=None):
    """Normalize values entered by a human while reviewing an AI draft."""
    existing = dict(existing or {})
    date_value = _parse_date(data.get('date') or existing.get('date'))
    amount = _decimal(data.get('amount') or existing.get('amount'))
    category = str(data.get('category') or existing.get('category') or '').strip()
    valid_categories = dict(OperationalExpense.CATEGORIES)
    category = next((v for v in valid_categories if v.lower() == category.lower()), '')
    payment = str(data.get('payment_method') or existing.get('payment_method') or '').strip()
    payment = next((v for v in PAYMENT_METHODS if v.lower() == payment.lower()), '')
    name = str(data.get('name') or existing.get('name') or '').strip()
    pond_raw = data.get('pond_id') if 'pond_id' in data else existing.get('pond_id')
    try:
        pond_id = int(pond_raw) if pond_raw not in (None, '', '0') else None
    except (TypeError, ValueError):
        pond_id = None
    if pond_id is not None and not Pond.objects.filter(pk=pond_id).exists():
        pond_id = None
    missing = []
    if not date_value: missing.append('date')
    if not category: missing.append('category')
    if not name: missing.append('name')
    if amount is None or amount <= 0: missing.append('amount')
    if not payment: missing.append('payment_method')
    return {
        'date': date_value.isoformat() if date_value else '',
        'category': category,
        'name': name,
        'amount': str(amount or Decimal('0')),
        'payment_method': payment,
        'pond_id': pond_id,
        'document_number': str(data.get('document_number') or existing.get('document_number') or '').strip()[:80],
        'notes': str(data.get('notes') or existing.get('notes') or '').strip(),
        'confidence': existing.get('confidence') if isinstance(existing.get('confidence'), dict) else {},
        'category_source': existing.get('category_source', 'human_review'),
        'missing_fields': missing,
        'cycle_id': cycle.id if cycle else existing.get('cycle_id'),
        'cycle_name': cycle.name if cycle else existing.get('cycle_name', ''),
    }


def create_expense_draft(user, command, extracted, uploaded_file, cycle, request=None):
    action = AIAction.objects.create(
        user=user,
        action='operational_expense.create',
        command=command or 'Analisis bukti pengeluaran dengan AI',
        payload=extracted,
        status='draft',
    )
    doc = AIOperationalExpenseDocument.objects.create(
        action=action,
        file=uploaded_file,
        original_name=Path(uploaded_file.name).name[:255],
        content_type=getattr(uploaded_file, 'content_type', '') or mimetypes.guess_type(uploaded_file.name)[0] or '',
        file_size=uploaded_file.size,
    )
    action.result = {'document_id': doc.id, 'extracted': extracted}
    action.save(update_fields=['result', 'updated_at'])
    record_ai_event(action, user, 'draft_created', {'document_id': doc.id, 'amount': extracted.get('amount'), 'category': extracted.get('category')}, request)
    return action


def _copy_document_to_expense(ai_doc, expense, user):
    ai_doc.file.open('rb')
    try:
        content = ai_doc.file.read()
    finally:
        ai_doc.file.close()
    target = ExpenseDocument.objects.create(
        expense=expense,
        original_name=ai_doc.original_name[:255],
        description='Bukti pengeluaran dianalisis AI',
        uploaded_by=user,
    )
    target.file.save(ai_doc.original_name[:255], ContentFile(content), save=True)
    return target


def execute_operational_expense(action, approver, request=None):
    """Create the real OperationalExpense from a completed AI draft.

    The review form's Save button is the final persistence action.  The
    financial transaction must not be rolled back merely because copying the
    optional AI evidence document fails; the transaction itself is the source
    of truth.  Evidence-copy errors are recorded in the AI result/audit log.
    """
    if action.status != 'draft':
        raise ValueError('Action ini sudah diproses.')

    p = dict(action.payload or {})
    amount = Decimal(str(p.get('amount') or '0'))
    required = {
        'date': p.get('date'),
        'category': p.get('category'),
        'name': str(p.get('name') or '').strip(),
        'amount': amount if amount > 0 else None,
        'payment_method': p.get('payment_method'),
    }
    missing = [k for k, v in required.items() if v in (None, '')]
    if missing:
        raise ValueError('Draft pengeluaran belum lengkap: ' + ', '.join(missing) + '.')

    cycle = CultivationCycle.objects.filter(pk=p.get('cycle_id')).first()
    if not cycle:
        raise ValueError('Siklus budidaya pada draft tidak ditemukan. Pilih ulang siklus dan analisis kembali.')

    expense = OperationalExpense.objects.create(
        cycle=cycle,
        date=date.fromisoformat(str(p['date'])),
        category=p['category'],
        pond_id=p.get('pond_id') or None,
        name=str(p['name'])[:150],
        amount=amount,
        payment_method=p.get('payment_method'),
        notes=p.get('notes', ''),
        document_number=str(p.get('document_number', ''))[:80],
    )

    document_errors = []
    for doc in action.expense_documents.all():
        try:
            _copy_document_to_expense(doc, expense, approver)
        except Exception as exc:
            document_errors.append(f'{doc.original_name or doc.file.name}: {exc}')

    now = timezone.now()
    result = {
        **(action.result or {}),
        'expense_id': expense.id,
        'amount': str(amount),
        'category': expense.category,
        'name': expense.name,
        'saved': True,
    }
    if document_errors:
        result['document_errors'] = document_errors

    action.status = 'executed'
    action.approved_by = approver
    action.approved_at = now
    action.executed_at = now
    action.result = result
    action.save(update_fields=['status', 'approved_by', 'approved_at', 'executed_at', 'result', 'updated_at'])
    record_ai_event(
        action,
        approver,
        'executed',
        {
            'expense_id': expense.id,
            'amount': str(amount),
            'document_errors': document_errors,
        },
        request,
    )
    return expense

