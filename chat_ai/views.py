from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.rbac import permission_required
from ponds.models import Pond
from operations.models import DailyParameter, DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord, Harvest
from .models import ChatSession, ChatMessage
from .services import ask_ollama, ollama_health

from cultivation.utils import get_selected_cycle


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
        parts.append(f'Data harian {latest_daily.date}: pakan {latest_daily.daily_feed_kg} kg, kode pakan {latest_daily.feed_code}, cuaca {latest_daily.weather}, treatment {latest_daily.treatment or "-"}.')
    if latest_anco:
        parts.append(f'Cek anco {latest_anco.date}: status {latest_anco.appetite_status}, rekomendasi sistem {latest_anco.recommendation}.')
    if latest_sampling:
        parts.append(f'Sampling {latest_sampling.date}: DOC {latest_sampling.doc}, ABW {latest_sampling.abw_g} g, size {latest_sampling.size}, ADG weekly {latest_sampling.adg_weekly}, FCR {latest_sampling.fcr}, biomassa {latest_sampling.biomass_kg} kg, SR {latest_sampling.estimated_sr}%, estimasi panen {latest_sampling.harvest_estimation}.')
    if latest_siphon:
        parts.append(f'Siphon {latest_siphon.date}: mati {latest_siphon.dead_count} ekor, hidup tersiphon {latest_siphon.live_count} ekor, indikator {latest_siphon.health_indicator}.')
    if latest_harvest:
        parts.append(f'Panen terakhir {latest_harvest.date}: {latest_harvest.harvest_type}, size {latest_harvest.size_text}, total {latest_harvest.total_kg} kg.')
    return ' '.join(parts)


def _is_ollama_error(answer):
    text = (answer or '').lower()
    return 'ollama belum tersedia' in text or 'gagal dihubungi' in text or 'connection refused' in text or 'timed out' in text


@login_required
@permission_required('chat.view')
def chat(request):
    ponds = Pond.objects.all()
    cycle = get_selected_cycle(request)
    session = ChatSession.objects.filter(user=request.user, cycle=cycle).order_by('-updated_at', '-created_at').first()
    if not session:
        session = ChatSession.objects.create(
            user=request.user,
            cycle=cycle,
            model_name=getattr(settings, 'OLLAMA_MODEL', 'gemma2:2b'),
        )

    if request.method == 'POST':
        msg = (request.POST.get('message') or '').strip()
        pond_id = request.POST.get('pond')
        if pond_id:
            session.pond_id = pond_id
            session.save(update_fields=['pond'])

        if not msg:
            messages.warning(request, 'Pertanyaan tidak boleh kosong.')
            return redirect('chat_ai:chat')

        context = _pond_ai_context(session.pond)
        context_snapshot = {
            'pond_id': session.pond_id,
            'pond_name': session.pond.name if session.pond else '',
            'context_text': context,
        }

        ChatMessage.objects.create(
            session=session,
            role='user',
            message=msg,
            context_snapshot=context_snapshot,
        )

        prompt = (
            'Anda adalah asisten manajemen tambak udang vaname untuk aplikasi Smart Shrimp Farm. '
            'Jawab praktis, aman, berbasis data, dan berikan rekomendasi operasional yang bisa dilakukan teknisi. '
            + context + ' Pertanyaan: ' + msg
        )
        answer = ask_ollama(prompt)
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            message=answer,
            context_snapshot=context_snapshot,
        )

        session.model_name = getattr(settings, 'OLLAMA_MODEL', 'gemma2:2b')
        if _is_ollama_error(answer):
            session.retention_type = ChatSession.RETENTION_ERROR
            session.error_message = answer[:1000]
        elif not session.is_important:
            session.retention_type = ChatSession.RETENTION_NORMAL
            session.error_message = ''
        session.save()
        return redirect('chat_ai:chat')

    return render(request, 'chat_ai/chat.html', {
        'session': session,
        'ponds': ponds,
        'ollama_health': ollama_health(),
    })


@login_required
@permission_required('chat.view')
def mark_important(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.is_important = True
    session.retention_type = ChatSession.RETENTION_IMPORTANT
    session.error_message = ''
    session.save(update_fields=['is_important', 'retention_type', 'error_message', 'updated_at'])
    messages.success(request, 'Percakapan ditandai penting dan akan disimpan permanen.')
    return redirect('chat_ai:chat')


@login_required
@permission_required('chat.view')
def unmark_important(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.is_important = False
    session.retention_type = ChatSession.RETENTION_NORMAL
    session.save(update_fields=['is_important', 'retention_type', 'updated_at'])
    messages.success(request, 'Percakapan dikembalikan menjadi percakapan biasa.')
    return redirect('chat_ai:chat')
