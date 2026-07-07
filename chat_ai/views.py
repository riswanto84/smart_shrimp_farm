from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from ponds.models import Pond
from operations.models import DailyParameter, DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord, Harvest
from .models import ChatSession, ChatMessage
from .services import ask_ollama, ollama_health


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


@login_required
@permission_required('chat.view')
def chat(request):
    ponds = Pond.objects.all()
    session = ChatSession.objects.filter(user=request.user).order_by('-created_at').first()
    if not session:
        session = ChatSession.objects.create(user=request.user)
    if request.method == 'POST':
        msg = request.POST['message']
        pond_id = request.POST.get('pond')
        if pond_id:
            session.pond_id = pond_id
            session.save()
        ChatMessage.objects.create(session=session, role='user', message=msg)
        context = _pond_ai_context(session.pond)
        prompt = (
            'Anda adalah asisten manajemen tambak udang vaname untuk aplikasi Smart Shrimp Farm. '
            'Jawab praktis, aman, berbasis data, dan berikan rekomendasi operasional yang bisa dilakukan teknisi. '
            + context + ' Pertanyaan: ' + msg
        )
        answer = ask_ollama(prompt)
        ChatMessage.objects.create(session=session, role='assistant', message=answer)
        return redirect('chat_ai:chat')
    return render(request, 'chat_ai/chat.html', {'session': session, 'ponds': ponds, 'ollama_health': ollama_health()})
