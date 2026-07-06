from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from ponds.models import Pond
from operations.models import DailyParameter
from .models import ChatSession, ChatMessage
from .services import ask_ollama
@login_required
@permission_required('chat.view')
def chat(request):
    ponds=Pond.objects.all(); session=ChatSession.objects.filter(user=request.user).order_by('-created_at').first()
    if not session: session=ChatSession.objects.create(user=request.user)
    if request.method=='POST':
        msg=request.POST['message']; pond_id=request.POST.get('pond')
        if pond_id: session.pond_id=pond_id; session.save()
        ChatMessage.objects.create(session=session, role='user', message=msg)
        context=''
        if session.pond:
            latest=DailyParameter.objects.filter(pond=session.pond).order_by('-date','-created_at').first()
            if latest: context=f'Data terakhir {session.pond.name}: DOC {latest.doc}, suhu {latest.temperature}, pH pagi {latest.ph_morning}, pH sore {latest.ph_evening}, DO pagi {latest.do_morning}, DO malam {latest.do_night}, salinitas {latest.salinity}. '
        answer=ask_ollama('Anda adalah asisten tambak udang vaname. Jawab singkat, praktis, dan aman. '+context+'Pertanyaan: '+msg)
        ChatMessage.objects.create(session=session, role='assistant', message=answer)
        return redirect('chat_ai:chat')
    return render(request,'chat_ai/chat.html',{'session':session,'ponds':ponds})
