from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.rbac import permission_required
from django.db.models import Sum
from ponds.models import Pond
from .models import DailyParameter, Treatment, FeedLog, Harvest
from chat_ai.services import ask_ollama
from core.reporting import get_date_range, filter_by_date_range, format_date_range, export_excel, export_pdf


def _parameter_queryset(request):
    date_from, date_to = get_date_range(request)
    items = DailyParameter.objects.select_related('pond', 'technician').order_by('-date')
    items = filter_by_date_range(items, 'date', date_from, date_to)
    pond = request.GET.get('pond') or ''
    if pond:
        items = items.filter(pond_id=pond)
    return items, date_from, date_to


def _parameter_rows(items):
    rows = []
    for i in items:
        rows.append([
            i.date.strftime('%d/%m/%Y'),
            i.pond.name,
            i.doc,
            i.temperature,
            i.ph_morning,
            i.ph_evening,
            i.do_morning,
            i.do_night,
            i.salinity,
            i.alkalinity,
            i.transparency,
            i.feed_kg,
            i.mortality,
            i.water_color,
            i.technician.username if i.technician else '-',
            i.ai_recommendation,
        ])
    return rows


@login_required
@permission_required('operations.parameters')
def parameters(request):
    items, date_from, date_to = _parameter_queryset(request)
    return render(request, 'operations/parameters.html', {'items': items, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all()})


@login_required
@permission_required('operations.parameters')
def export_parameters_excel(request):
    items, date_from, date_to = _parameter_queryset(request)
    return export_excel(
        'laporan_parameter_harian',
        'Laporan Parameter Harian',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kolam', 'DOC', 'Suhu', 'pH Pagi', 'pH Sore', 'DO Pagi', 'DO Malam', 'Salinitas', 'Alkalinitas', 'Kecerahan', 'Pakan Kg', 'Kematian', 'Warna Air', 'Teknisi', 'Rekomendasi AI'],
        _parameter_rows(items),
    )


@login_required
@permission_required('operations.parameters')
def export_parameters_pdf(request):
    items, date_from, date_to = _parameter_queryset(request)
    rows = _parameter_rows(items)
    short_rows = [[r[0], r[1], r[2], r[3], r[5], r[7], r[8], r[11], r[14], (r[15] or '')[:80]] for r in rows]
    return export_pdf(
        'laporan_parameter_harian',
        'Laporan Parameter Harian',
        f'Periode: {format_date_range(date_from, date_to)}',
        ['Tanggal', 'Kolam', 'DOC', 'Suhu', 'pH Sore', 'DO Malam', 'Salinitas', 'Pakan', 'Teknisi', 'AI'],
        short_rows,
    )


@login_required
@permission_required('operations.parameters')
def add_parameter(request):
    ponds = Pond.objects.all()
    if request.method == 'POST':
        obj = DailyParameter.objects.create(pond_id=request.POST['pond'], technician=request.user, date=request.POST['date'], doc=request.POST.get('doc') or 0, temperature=request.POST.get('temperature') or None, ph_morning=request.POST.get('ph_morning') or None, ph_evening=request.POST.get('ph_evening') or None, do_morning=request.POST.get('do_morning') or None, do_night=request.POST.get('do_night') or None, salinity=request.POST.get('salinity') or None, alkalinity=request.POST.get('alkalinity') or None, transparency=request.POST.get('transparency') or None, feed_kg=request.POST.get('feed_kg') or 0, mortality=request.POST.get('mortality') or 0, water_color=request.POST.get('water_color', ''), notes=request.POST.get('notes', ''))
        if 'analyse' in request.POST:
            prompt = f"Anda asisten tambak udang vaname. Analisa parameter kolam {obj.pond.name}: DOC {obj.doc}, suhu {obj.temperature}, pH pagi {obj.ph_morning}, pH sore {obj.ph_evening}, DO pagi {obj.do_morning}, DO malam {obj.do_night}, salinitas {obj.salinity}, alkalinitas {obj.alkalinity}. Berikan status, risiko, dan rekomendasi singkat."
            obj.ai_recommendation = ask_ollama(prompt); obj.save()
        return redirect('operations:parameters')
    return render(request, 'operations/parameter_form.html', {'ponds': ponds})


def _harvest_queryset(request):
    date_from, date_to = get_date_range(request)
    items = Harvest.objects.select_related('pond').order_by('-date')
    items = filter_by_date_range(items, 'date', date_from, date_to)
    pond = request.GET.get('pond') or ''
    if pond:
        items = items.filter(pond_id=pond)
    return items, date_from, date_to


def _harvest_rows(items):
    rows = []
    for i in items:
        rows.append([
            i.date.strftime('%d/%m/%Y'),
            i.pond.name,
            i.harvest_type,
            i.size_text,
            float(i.total_kg),
            i.notes,
        ])
    return rows


@login_required
@permission_required('operations.harvests')
def harvests(request):
    items, date_from, date_to = _harvest_queryset(request)
    total_kg = items.aggregate(s=Sum('total_kg'))['s'] or 0
    return render(request, 'operations/harvests.html', {'items': items, 'date_from': date_from, 'date_to': date_to, 'ponds': Pond.objects.all(), 'total_kg': total_kg})


@login_required
@permission_required('operations.harvests')
def export_harvests_excel(request):
    items, date_from, date_to = _harvest_queryset(request)
    rows = _harvest_rows(items)
    total_kg = items.aggregate(s=Sum('total_kg'))['s'] or 0
    return export_excel('laporan_panen', 'Laporan Panen', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal', 'Kolam', 'Jenis Panen', 'Size', 'Total Kg', 'Catatan'], rows, [['', '', '', 'TOTAL', float(total_kg), '']])


@login_required
@permission_required('operations.harvests')
def export_harvests_pdf(request):
    items, date_from, date_to = _harvest_queryset(request)
    rows = _harvest_rows(items)
    total_kg = items.aggregate(s=Sum('total_kg'))['s'] or 0
    return export_pdf('laporan_panen', 'Laporan Panen', f'Periode: {format_date_range(date_from, date_to)}', ['Tanggal', 'Kolam', 'Jenis', 'Size', 'Kg', 'Catatan'], rows, [['', '', '', 'TOTAL', total_kg, '']])


@login_required
@permission_required('operations.harvests')
def add_harvest(request):
    ponds = Pond.objects.all()
    if request.method == 'POST':
        Harvest.objects.create(pond_id=request.POST['pond'], date=request.POST['date'], harvest_type=request.POST.get('harvest_type', 'Parsial'), size_text=request.POST.get('size_text', ''), total_kg=request.POST.get('total_kg') or 0, notes=request.POST.get('notes', ''))
        return redirect('operations:harvests')
    return render(request, 'operations/harvest_form.html', {'ponds': ponds})
