from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.db.models import Avg, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from accounts.rbac import owner_required
from finance.models import OperationalExpense
from operations.models import (AncoCheck, DailyParameter, Harvest, SamplingRecord,
                               SiphonRecord, Stocking)
from ponds.models import Pond
from sales.models import Sale
from chat_ai.models import ChatMessage
from chat_ai.services import ollama_health
from .forms import CultivationCycleForm
from .models import CultivationCycle
from .utils import get_selected_cycle


def _d(value):
    try:
        return Decimal(value or 0)
    except Exception:
        return Decimal('0')


def _cycle_data(cycle):
    ponds = Pond.objects.all().order_by('name')
    parameters = DailyParameter.objects.filter(cycle=cycle).select_related('pond')
    samplings = SamplingRecord.objects.filter(cycle=cycle).select_related('pond')
    siphons = SiphonRecord.objects.filter(cycle=cycle).select_related('pond')
    ancos = AncoCheck.objects.filter(cycle=cycle).select_related('pond')
    harvests = Harvest.objects.filter(cycle=cycle).select_related('pond')
    stockings = Stocking.objects.filter(cycle=cycle).select_related('pond')
    expenses = OperationalExpense.objects.filter(cycle=cycle)
    sales = Sale.objects.filter(cycle=cycle)

    latest_by_pond = {}
    for row in samplings.order_by('pond_id', '-date', '-id'):
        latest_by_pond.setdefault(row.pond_id, row)
    latest_samples = list(latest_by_pond.values())

    biomass = sum((_d(x.biomass_kg) for x in latest_samples), Decimal('0'))
    avg_abw = (sum((_d(x.abw_g) for x in latest_samples), Decimal('0')) / len(latest_samples)) if latest_samples else Decimal('0')
    avg_fcr = (sum((_d(x.fcr) for x in latest_samples), Decimal('0')) / len(latest_samples)) if latest_samples else Decimal('0')
    avg_sr = (sum((_d(x.estimated_sr) for x in latest_samples), Decimal('0')) / len(latest_samples)) if latest_samples else Decimal('0')
    avg_adg = (sum((_d(x.adg_weekly) for x in latest_samples), Decimal('0')) / len(latest_samples)) if latest_samples else Decimal('0')
    seed_total = stockings.aggregate(v=Sum('seed_count'))['v'] or 0
    harvest_total = harvests.aggregate(v=Sum('total_kg'))['v'] or Decimal('0')
    expense_total = expenses.aggregate(v=Sum('amount'))['v'] or Decimal('0')
    sales_total = sales.aggregate(v=Sum('total_amount'))['v'] or Decimal('0')
    profit = sales_total - expense_total

    pond_rows=[]
    for pond in ponds:
        sample=latest_by_pond.get(pond.id)
        pond_rows.append({
            'pond': pond,
            'sample': sample,
            'biomass': _d(sample.biomass_kg) if sample else Decimal('0'),
            'sr': _d(sample.estimated_sr) if sample else Decimal('0'),
            'abw': _d(sample.abw_g) if sample else Decimal('0'),
            'fcr': _d(sample.fcr) if sample else Decimal('0'),
        })

    timeline=[]
    for x in samplings.order_by('date'):
        timeline.append({'date': x.date, 'biomass': float(x.biomass_kg or 0), 'abw': float(x.abw_g or 0), 'adg': float(x.adg_weekly or 0), 'fcr': float(x.fcr or 0), 'sr': float(x.estimated_sr or 0)})
    max_biomass=max([x['biomass'] for x in timeline] or [1])
    for x in timeline:
        x['biomass_pct']=min(100, round(x['biomass']/max_biomass*100, 1)) if max_biomass else 0

    return {
        'ponds': ponds, 'pond_rows': pond_rows, 'parameters': parameters,
        'samplings': samplings, 'siphons': siphons, 'ancos': ancos,
        'harvests': harvests, 'stockings': stockings, 'expenses': expenses,
        'sales': sales, 'timeline': timeline[-14:], 'latest_samples': latest_samples,
        'biomass': biomass, 'avg_abw': avg_abw, 'avg_fcr': avg_fcr,
        'avg_sr': avg_sr, 'avg_adg': avg_adg, 'seed_total': seed_total,
        'harvest_total': harvest_total, 'expense_total': expense_total,
        'sales_total': sales_total, 'profit': profit,
        'parameter_count': parameters.count(), 'anco_count': ancos.count(),
        'sampling_count': samplings.count(), 'siphon_count': siphons.count(),
        'harvest_count': harvests.count(),
    }


@owner_required
def cycle_list(request):
    return render(request, 'cultivation/cycle_list.html', {'cycles': CultivationCycle.objects.all()})


@owner_required
def cycle_form(request, pk=None):
    obj = get_object_or_404(CultivationCycle, pk=pk) if pk else None
    if request.method == 'POST':
        form = CultivationCycleForm(request.POST, instance=obj)
        if form.is_valid():
            cycle = form.save()
            request.session['selected_cycle_id'] = cycle.pk
            messages.success(request, 'Siklus budidaya berhasil disimpan.')
            return redirect('cultivation:dashboard')
        messages.error(request, 'Data siklus belum valid. Periksa kembali kolom yang ditandai.')
    else:
        form = CultivationCycleForm(instance=obj)
    return render(request, 'cultivation/cycle_form.html', {'obj': obj, 'form': form, 'statuses': CultivationCycle.STATUS_CHOICES})


@owner_required
@require_POST
def select_cycle(request):
    cycle = get_object_or_404(CultivationCycle, pk=request.POST.get('cycle'))
    request.session['selected_cycle_id'] = cycle.pk
    messages.success(request, f'Siklus tampilan diubah ke {cycle.name}.')
    return redirect(request.META.get('HTTP_REFERER') or 'cultivation:dashboard')


@owner_required
def cycle_dashboard(request):
    cycle=get_selected_cycle(request)
    if not cycle:
        messages.info(request, 'Buat siklus budidaya terlebih dahulu.')
        return redirect('cultivation:add')
    data=_cycle_data(cycle)
    data.update({'cycle': cycle, 'ollama_status': ollama_health(timeout=2), 'today': timezone.localdate()})
    return render(request, 'cultivation/dashboard.html', data)


@owner_required
def cycle_report(request):
    cycle=get_selected_cycle(request)
    if not cycle:
        return redirect('cultivation:add')
    data=_cycle_data(cycle)
    data.update({'cycle': cycle})
    return render(request, 'cultivation/report.html', data)


def _report_rows(data):
    return [
        ('Durasi target', f"{data['cycle'].target_duration_days} hari"),
        ('Progres', f"{data['cycle'].progress_percent}%"),
        ('Jumlah kolam', str(data['ponds'].count())),
        ('Benur ditebar', f"{data['seed_total']:,} ekor".replace(',', '.')),
        ('Biomassa estimasi', f"{data['biomass']:,.2f} kg"),
        ('Rata-rata ABW', f"{data['avg_abw']:,.2f} gram"),
        ('Rata-rata ADG', f"{data['avg_adg']:,.3f} g/hari"),
        ('Rata-rata SR', f"{data['avg_sr']:,.2f}%"),
        ('Rata-rata FCR', f"{data['avg_fcr']:,.3f}"),
        ('Panen aktual', f"{data['harvest_total']:,.2f} kg"),
        ('Total penjualan', f"Rp {data['sales_total']:,.0f}"),
        ('Total pengeluaran', f"Rp {data['expense_total']:,.0f}"),
        ('Laba/rugi', f"Rp {data['profit']:,.0f}"),
    ]


@owner_required
def cycle_report_excel(request):
    cycle=get_selected_cycle(request, required=True); data=_cycle_data(cycle); data['cycle']=cycle
    wb=Workbook(); ws=wb.active; ws.title='Ringkasan Siklus'
    ws.append(['LAPORAN PER SIKLUS', cycle.name]); ws.append(['Periode', f"{cycle.start_date:%d/%m/%Y} - {cycle.target_end_date:%d/%m/%Y}"])
    ws.append([]); ws.append(['Indikator','Nilai'])
    for row in _report_rows(data): ws.append(list(row))
    ws.append([]); ws.append(['Kolam','Luas m2','ABW','SR %','Biomassa kg','FCR'])
    for x in data['pond_rows']:
        ws.append([x['pond'].name, float(x['pond'].area_m2 or 0), float(x['abw']), float(x['sr']), float(x['biomass']), float(x['fcr'])])
    for cell in ws[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='083B72')
    for cell in ws[4]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='1261A0')
    for col in 'ABCDEF': ws.column_dimensions[col].width=22
    buf=BytesIO(); wb.save(buf); buf.seek(0)
    response=HttpResponse(buf.read(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']=f'attachment; filename="laporan_siklus_{cycle.pk}.xlsx"'; return response


@owner_required
def cycle_report_pdf(request):
    cycle=get_selected_cycle(request, required=True); data=_cycle_data(cycle); data['cycle']=cycle
    response=HttpResponse(content_type='application/pdf'); response['Content-Disposition']=f'attachment; filename="laporan_siklus_{cycle.pk}.pdf"'
    doc=SimpleDocTemplate(response,pagesize=landscape(A4),rightMargin=12*mm,leftMargin=12*mm,topMargin=12*mm,bottomMargin=12*mm)
    styles=getSampleStyleSheet(); story=[Paragraph(f'Laporan Per Siklus - {cycle.name}',styles['Title']),Paragraph(f'Periode {cycle.start_date:%d/%m/%Y} s.d. {cycle.target_end_date:%d/%m/%Y}',styles['Normal']),Spacer(1,8)]
    table=Table([['Indikator','Nilai']]+[list(x) for x in _report_rows(data)],colWidths=[80*mm,100*mm])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#083B72')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#CBD5E1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFC')]),('PADDING',(0,0),(-1,-1),7)])); story.append(table); story.append(Spacer(1,10))
    rows=[['Kolam','Luas','ABW','SR','Biomassa','FCR']]+[[x['pond'].name,str(x['pond'].area_m2),str(x['abw']),str(x['sr']),str(x['biomass']),str(x['fcr'])] for x in data['pond_rows']]
    t2=Table(rows,repeatRows=1); t2.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1261A0')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#CBD5E1')),('ALIGN',(1,1),(-1,-1),'RIGHT'),('PADDING',(0,0),(-1,-1),6)])); story.append(t2)
    doc.build(story); return response
