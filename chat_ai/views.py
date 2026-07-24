import base64
import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.rbac import permission_required
from cultivation.utils import get_selected_cycle
from operations.models import DailyParameter, DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord, Harvest
from ponds.models import Pond
from .file_utils import extract_text, validate_upload
from .models import ChatAttachment, ChatMessage, ChatSession
from .services import active_model, ollama_health, stream_ollama


def _pond_ai_context(pond):
    if not pond:
        return ''
    parts = [f'Konteks kolam {pond.name}.']
    latest_parameter = DailyParameter.objects.filter(pond=pond).order_by('-date', '-created_at').first()
    latest_daily = DailyPondRecord.objects.filter(pond=pond).order_by('-date').first()
    latest_anco = AncoCheck.objects.filter(pond=pond).order_by('-date').first()
    latest_sampling = SamplingRecord.objects.filter(pond=pond).order_by('-date').first()
    latest_siphon = SiphonRecord.objects.filter(pond=pond).order_by('-date').first()
    latest_harvest = Harvest.objects.filter(pond=pond).order_by('-date').first()
    if latest_parameter:
        parts.append(f'Parameter terakhir {latest_parameter.date}: DOC {latest_parameter.doc}, suhu {latest_parameter.temperature}, pH pagi {latest_parameter.ph_morning}, pH sore {latest_parameter.ph_evening}, DO pagi {latest_parameter.do_morning}, DO malam {latest_parameter.do_night}, salinitas {latest_parameter.salinity}.')
    if latest_daily:
        parts.append(f'Data harian {latest_daily.date}: pakan {latest_daily.daily_feed_kg} kg, cuaca {latest_daily.weather}, treatment {latest_daily.treatment or "-"}.')
    if latest_anco:
        parts.append(f'Cek anco {latest_anco.date}: status {latest_anco.appetite_status}, rekomendasi sistem {latest_anco.recommendation}.')
    if latest_sampling:
        parts.append(f'Sampling {latest_sampling.date}: DOC {latest_sampling.doc}, ABW {latest_sampling.abw_g} g, size {latest_sampling.size}, ADG weekly {latest_sampling.adg_weekly}, FCR {latest_sampling.fcr}, biomassa {latest_sampling.biomass_kg} kg, SR {latest_sampling.estimated_sr}%, estimasi panen {latest_sampling.harvest_estimation}.')
    if latest_siphon:
        parts.append(f'Siphon {latest_siphon.date}: mati {latest_siphon.dead_count} ekor, hidup tersiphon {latest_siphon.live_count} ekor, indikator {latest_siphon.health_indicator}.')
    if latest_harvest:
        parts.append(f'Panen terakhir {latest_harvest.date}: {latest_harvest.harvest_type}, size {latest_harvest.size_text}, total {latest_harvest.total_kg} kg.')
    return ' '.join(parts)


def _session_for_user(request, session_id=None):
    cycle = get_selected_cycle(request)
    if session_id:
        return get_object_or_404(ChatSession, id=session_id, user=request.user)
    session = ChatSession.objects.filter(user=request.user).filter(Q(cycle=cycle) | Q(cycle__isnull=True)).order_by('-updated_at').first()
    return session or ChatSession.objects.create(user=request.user, cycle=cycle, model_name=active_model())


def _serialize_message(message):
    return {
        'id': message.id,
        'role': message.role,
        'message': message.message,
        'is_complete': message.is_complete,
        'created_at': message.created_at.isoformat(),
        'attachments': [
            {'name': a.original_name, 'url': a.file.url, 'size': a.size, 'content_type': a.content_type}
            for a in message.attachments.all()
        ],
    }


@login_required
@permission_required('chat.view')
def chat(request):
    session_id = request.GET.get('session')
    session = _session_for_user(request, session_id)
    sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')[:100]
    return render(request, 'chat_ai/chat.html', {
        'session': session,
        'sessions': sessions,
        'ponds': Pond.objects.all(),
        'ollama_health': ollama_health(),
        'max_upload_mb': getattr(settings, 'CHAT_AI_MAX_UPLOAD_MB', 15),
    })


@login_required
@permission_required('chat.view')
@require_POST
def new_session(request):
    cycle = get_selected_cycle(request)
    session = ChatSession.objects.create(user=request.user, cycle=cycle, model_name=active_model())
    return JsonResponse({'ok': True, 'id': session.id, 'title': session.title})


@login_required
@permission_required('chat.view')
def session_messages(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    return JsonResponse({
        'session': {'id': session.id, 'title': session.title, 'pond_id': session.pond_id, 'is_important': session.is_important},
        'messages': [_serialize_message(m) for m in session.messages.prefetch_related('attachments').all()],
    })


@login_required
@permission_required('chat.view')
@require_POST
def delete_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.delete()
    return JsonResponse({'ok': True})


@login_required
@permission_required('chat.view')
@require_POST
def rename_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    title = (request.POST.get('title') or '').strip()[:150]
    if not title:
        return JsonResponse({'ok': False, 'error': 'Judul tidak boleh kosong.'}, status=400)
    session.title = title
    session.save(update_fields=['title', 'updated_at'])
    return JsonResponse({'ok': True, 'title': title})


@login_required
@permission_required('chat.view')
@require_POST
def stream_chat(request):
    msg = (request.POST.get('message') or '').strip()
    session = _session_for_user(request, request.POST.get('session_id'))
    pond_id = request.POST.get('pond')
    uploads = request.FILES.getlist('files')
    if not msg and not uploads:
        return JsonResponse({'error': 'Tulis pesan atau pilih file.'}, status=400)
    if len(uploads) > 5:
        return JsonResponse({'error': 'Maksimal 5 file per pesan.'}, status=400)
    try:
        for uploaded in uploads:
            validate_upload(uploaded)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    if pond_id:
        session.pond = get_object_or_404(Pond, id=pond_id)
        session.save(update_fields=['pond', 'updated_at'])

    context = _pond_ai_context(session.pond)
    snapshot = {'pond_id': session.pond_id, 'pond_name': session.pond.name if session.pond else '', 'context_text': context}
    user_message = ChatMessage.objects.create(session=session, role='user', message=msg or 'Mohon analisis file terlampir.', context_snapshot=snapshot)

    extracted_sections = []
    image_payloads = []
    for uploaded in uploads:
        attachment = ChatAttachment.objects.create(
            message=user_message, file=uploaded, original_name=uploaded.name,
            content_type=uploaded.content_type or '', size=uploaded.size,
        )
        text, error = extract_text(attachment.file.path, attachment.original_name)
        attachment.extracted_text = text
        attachment.extraction_error = error
        attachment.save(update_fields=['extracted_text', 'extraction_error'])
        if text:
            extracted_sections.append(f'\n--- Isi file: {attachment.original_name} ---\n{text}')
        if attachment.extension in {'.png', '.jpg', '.jpeg', '.webp'}:
            with attachment.file.open('rb') as fh:
                image_payloads.append(base64.b64encode(fh.read()).decode('ascii'))

    if session.messages.count() <= 1 or session.title == 'Percakapan Baru':
        base = msg or (uploads[0].name if uploads else 'Percakapan Baru')
        session.title = base[:70]

    assistant_message = ChatMessage.objects.create(session=session, role='assistant', message='', context_snapshot=snapshot, is_complete=False)
    session.model_name = active_model()
    session.error_message = ''
    session.save(update_fields=['title', 'model_name', 'error_message', 'updated_at'])

    system_prompt = (
        'Anda adalah Smart Shrimp AI, asisten profesional dalam aplikasi Smart Shrimp Farm. '
        'Jawab dalam Bahasa Indonesia yang jelas, praktis, berbasis data, dan tidak mengarang angka. '
        'Untuk saran budidaya, jelaskan risiko dan tindakan pemantauan. Gunakan format markdown bila membantu. '
        'Anda dapat menganalisis data tambak dan isi dokumen yang diberikan pengguna.'
    )
    current_content = msg or 'Analisis file terlampir.'
    if context:
        current_content += f'\n\nDATA KONTEKS TAMBAK:\n{context}'
    if extracted_sections:
        current_content += '\n'.join(extracted_sections)

    history_qs = session.messages.exclude(id__in=[assistant_message.id]).order_by('-created_at')[:20]
    history = list(reversed(list(history_qs)))
    ollama_messages = [{'role': 'system', 'content': system_prompt}]
    for item in history:
        content = current_content if item.id == user_message.id else item.message
        ollama_messages.append({'role': item.role, 'content': content})

    def event_stream():
        full_text = ''
        try:
            yield json.dumps({'type': 'start', 'user_message': _serialize_message(user_message), 'assistant_id': assistant_message.id, 'session_title': session.title}, ensure_ascii=False) + '\n'
            for chunk in stream_ollama(ollama_messages, model=session.model_name, images=image_payloads):
                full_text += chunk
                yield json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False) + '\n'
            assistant_message.message = full_text
            assistant_message.is_complete = True
            assistant_message.save(update_fields=['message', 'is_complete'])
            yield json.dumps({'type': 'done', 'message_id': assistant_message.id}, ensure_ascii=False) + '\n'
        except GeneratorExit:
            assistant_message.message = full_text
            assistant_message.is_complete = False
            assistant_message.save(update_fields=['message', 'is_complete'])
            raise
        except Exception as exc:
            error_text = f'Gagal menghubungi Ollama: {exc}'
            assistant_message.message = full_text or error_text
            assistant_message.is_complete = False
            assistant_message.save(update_fields=['message', 'is_complete'])
            session.retention_type = ChatSession.RETENTION_ERROR
            session.error_message = error_text[:1000]
            session.save(update_fields=['retention_type', 'error_message', 'updated_at'])
            yield json.dumps({'type': 'error', 'error': error_text}, ensure_ascii=False) + '\n'

    response = StreamingHttpResponse(event_stream(), content_type='application/x-ndjson; charset=utf-8')
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@permission_required('chat.view')
@require_POST
def mark_important(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.is_important = True
    session.retention_type = ChatSession.RETENTION_IMPORTANT
    session.error_message = ''
    session.save(update_fields=['is_important', 'retention_type', 'error_message', 'updated_at'])
    return JsonResponse({'ok': True, 'important': True})


@login_required
@permission_required('chat.view')
@require_POST
def unmark_important(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.is_important = False
    session.retention_type = ChatSession.RETENTION_NORMAL
    session.save(update_fields=['is_important', 'retention_type', 'updated_at'])
    return JsonResponse({'ok': True, 'important': False})
