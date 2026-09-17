from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, KeepTogether, LongTable,
)

from .models import CultivationCycle
from .services import build_cycle_history_metrics
from operations.models import (
    Stocking, DailyParameter, Treatment, FeedLog, Harvest,
    DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord,
)
from finance.models import OperationalExpense, ExpenseDocument, OtherRevenue, TradeAccount, TradePayment
from finance.services.profit_loss import calculate_profit_loss, INVALID_SALE_STATUSES
from sales.models import Sale, SaleItem, SaleDocument


ZERO = Decimal('0')


def _n(value, decimals=2):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0
    raw = f'{value:,.{decimals}f}'
    return raw.replace(',', 'X').replace('.', ',').replace('X', '.')


def _rp(value, decimals=0):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0
    sign = '-' if value < 0 else ''
    return f'Rp {sign}{_n(abs(value), decimals)}'


def _d(value):
    try:
        return Decimal(str(value or 0))
    except Exception:
        return ZERO


def _date(value):
    return value.strftime('%d/%m/%Y') if value else '-'


def _txt(value, limit=500):
    text = '' if value is None else str(value)
    return text if len(text) <= limit else text[:limit - 1] + '…'


def _p(value, style):
    text = _txt(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
    return Paragraph(text or '-', style)


def _safe_name(name):
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in name).strip('_') or 'siklus'


def _section(title, style):
    return [Spacer(1, 2*mm), Paragraph(title, style), Spacer(1, 1.5*mm)]


def _detail_table(story, title, headers, rows, styles, widths=None, landscape_table=True):
    story.extend(_section(title, styles['section']))
    if not rows:
        story.append(_p('Tidak ada data tercatat pada siklus ini.', styles['muted']))
        return

    data = [[_p(h, styles['th']) for h in headers]]
    data.extend([[_p(v, styles['td']) for v in row] for row in rows])
    if widths is None:
        weights = []
        for i, h in enumerate(headers):
            mx = len(str(h))
            for r in rows[:100]:
                mx = max(mx, min(len(str(r[i] if i < len(r) else '')), 30))
            weights.append(max(5, min(mx, 28)))
        total = sum(weights) or 1
        available_width = landscape(A4)[0] - (24 * mm)
        widths = [available_width * w / total for w in weights]

    table = LongTable(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#082F5B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#DCE7F1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F3F7FB')]),
        ('LEFTPADDING', (0,0), (-1,-1), 2.2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2.2),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
    ]))
    story.append(table)
    story.append(Spacer(1, 3*mm))


def generate_comprehensive_cycle_pdf(request, pk):
    cycle = get_object_or_404(CultivationCycle, pk=pk)
    if cycle.status != CultivationCycle.STATUS_COMPLETED:
        messages.warning(request, 'Laporan akhir hanya tersedia untuk siklus yang sudah selesai.')
        return redirect('cultivation:list')

    # Semua queryset dibatasi langsung ke cycle agar arsip tidak tercampur dengan Siklus 9.
    stocking = Stocking.objects.filter(cycle=cycle).select_related('pond').order_by('date', 'pond__name', 'id')
    daily = DailyPondRecord.objects.filter(cycle=cycle).select_related('pond', 'technician').order_by('date', 'pond__name', 'id')
    params = DailyParameter.objects.filter(cycle=cycle).select_related('pond', 'technician').order_by('date', 'pond__name', 'id')
    anco = AncoCheck.objects.filter(cycle=cycle).select_related('pond', 'technician').order_by('date', 'pond__name', 'id')
    sampling = SamplingRecord.objects.filter(cycle=cycle).select_related('pond').order_by('date', 'pond__name', 'id')
    siphon = SiphonRecord.objects.filter(cycle=cycle).select_related('pond', 'technician').order_by('date', 'pond__name', 'id')
    treatments = Treatment.objects.filter(cycle=cycle).select_related('pond').order_by('date', 'pond__name', 'id')
    feedlogs = FeedLog.objects.filter(cycle=cycle).select_related('pond').order_by('date', 'pond__name', 'id')
    harvests = Harvest.objects.filter(cycle=cycle).select_related('pond').order_by('date', 'pond__name', 'id')

    sales = Sale.objects.filter(cycle=cycle).exclude(status__in=INVALID_SALE_STATUSES).select_related('customer', 'cashier').prefetch_related('items', 'documents').order_by('date', 'id')
    sale_all = Sale.objects.filter(cycle=cycle).select_related('customer').prefetch_related('items', 'documents').order_by('date', 'id')
    expenses = OperationalExpense.objects.filter(cycle=cycle).select_related('pond', 'fixed_asset', 'trade_payment').prefetch_related('documents').order_by('date', 'id')
    other_revenues = OtherRevenue.objects.filter(cycle=cycle).order_by('date', 'id')
    trades = TradeAccount.objects.filter(cycle=cycle).prefetch_related('payments', 'documents').order_by('account_type', 'due_date', 'id')

    metrics = build_cycle_history_metrics(cycle)
    pl = calculate_profit_loss(cycle=cycle, date_from=cycle.start_date, date_to=cycle.actual_end_date or cycle.target_end_date)

    total_sale_kg = sales.aggregate(v=Sum('total_kg'))['v'] or ZERO
    total_sale_amount = sales.aggregate(v=Sum('total_amount'))['v'] or ZERO
    expense_cash = expenses.filter(is_capital_expenditure=False).exclude(category='Penyusutan').aggregate(v=Sum('amount'))['v'] or ZERO
    capital_expense = expenses.filter(is_capital_expenditure=True).aggregate(v=Sum('amount'))['v'] or ZERO
    total_other_revenue = other_revenues.aggregate(v=Sum('gross_amount'))['v'] or ZERO
    receivable_original = trades.filter(account_type=TradeAccount.RECEIVABLE).aggregate(v=Sum('original_amount'))['v'] or ZERO
    payable_original = trades.filter(account_type=TradeAccount.PAYABLE).aggregate(v=Sum('original_amount'))['v'] or ZERO
    receivable_outstanding = sum((_d(t.outstanding_amount) for t in trades if t.account_type == TradeAccount.RECEIVABLE), ZERO)
    payable_outstanding = sum((_d(t.outstanding_amount) for t in trades if t.account_type == TradeAccount.PAYABLE), ZERO)
    total_trade_paid = sum((_d(p.amount) for t in trades for p in t.payments.all()), ZERO)

    buffer = BytesIO()
    page_size = landscape(A4)
    navy = colors.HexColor('#082F5B')
    blue = colors.HexColor('#176FD1')
    gold = colors.HexColor('#E4AE21')
    light = colors.HexColor('#F3F7FB')
    border = colors.HexColor('#DCE7F1')
    text = colors.HexColor('#17324F')
    muted = colors.HexColor('#667C93')
    green = colors.HexColor('#12835B')
    red = colors.HexColor('#C8323A')

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('rtitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=19, leading=22, textColor=colors.white, alignment=TA_LEFT))
    styles.add(ParagraphStyle('rsub', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#DDEBFA')))
    styles.add(ParagraphStyle('section', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=navy, spaceBefore=2, spaceAfter=5))
    styles.add(ParagraphStyle('td', parent=styles['Normal'], fontSize=6.1, leading=7.5, textColor=text))
    styles.add(ParagraphStyle('th', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6.1, leading=7.5, textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle('muted', parent=styles['Normal'], fontSize=7.2, leading=9, textColor=muted))
    styles.add(ParagraphStyle('metric_label', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6.5, textColor=muted))
    styles.add(ParagraphStyle('metric_value', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=navy))
    styles.add(ParagraphStyle('small', parent=styles['Normal'], fontSize=6.7, leading=8.5, textColor=text))
    styles.add(ParagraphStyle('right', parent=styles['Normal'], fontSize=7, leading=9, textColor=text, alignment=TA_RIGHT))

    def footer(canvas, doc):
        canvas.saveState()
        w, h = page_size
        canvas.setFillColor(navy)
        canvas.rect(0, h-7*mm, w, 7*mm, fill=1, stroke=0)
        canvas.setFillColor(gold)
        canvas.rect(0, h-8.3*mm, w, 1.3*mm, fill=1, stroke=0)
        canvas.setFont('Helvetica-Bold', 7.5)
        canvas.setFillColor(colors.white)
        canvas.drawString(12*mm, h-4.7*mm, 'UDANG EMAS NUSANTARA  •  SMART SHRIMP FARM')
        canvas.setStrokeColor(border)
        canvas.line(12*mm, 11*mm, w-12*mm, 11*mm)
        canvas.setFillColor(muted)
        canvas.setFont('Helvetica', 6.5)
        canvas.drawString(12*mm, 6.5*mm, 'Laporan akhir siklus — seluruh data yang terikat pada siklus terpilih.')
        canvas.drawRightString(w-12*mm, 6.5*mm, f'Halaman {doc.page}')
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=page_size, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=15*mm,
                            title=f'Laporan Akhir {cycle.name}', author='Smart Shrimp Farm - Udang Emas Nusantara')
    story = []

    logo_path = Path(settings.BASE_DIR) / 'static' / 'img' / 'logo_uen_report_black.png'
    logo = Image(str(logo_path), width=24*mm, height=24*mm, kind='proportional') if logo_path.exists() else Spacer(24*mm, 24*mm)
    period_end = cycle.actual_end_date or cycle.target_end_date
    hero = Table([[logo, [Paragraph('LAPORAN AKHIR SIKLUS BUDIDAYA', styles['rsub']), Paragraph(cycle.name, styles['rtitle']), Paragraph(f'Periode {_date(cycle.start_date)} – {_date(period_end)}  •  Status: {cycle.get_status_display()}', styles['rsub'])]]], colWidths=[30*mm, doc.width-30*mm])
    hero.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),navy),('BOX',(0,0),(-1,-1),0.7,gold),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),3*mm),('RIGHTPADDING',(0,0),(-1,-1),3*mm)]))
    story += [hero, Spacer(1, 4*mm)]

    # Ringkasan eksekutif.
    metric_values = [
        ('PRODUKSI RIIL', f'{_n(metrics["total_harvest_kg"],2)} kg'),
        ('OMZET PENJUALAN', _rp(total_sale_amount)),
        ('BIAYA OPERASIONAL', _rp(expense_cash)),
        ('LABA/RUGI', _rp(pl['profit'])),
    ]
    mdata = [[_p(a, styles['metric_label']) for a,b in metric_values], [_p(b, styles['metric_value']) for a,b in metric_values]]
    mt = Table(mdata, colWidths=[doc.width/4]*4, rowHeights=[6*mm, 9*mm])
    mt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.4,border),('BACKGROUND',(0,0),(-1,-1),colors.white),('LEFTPADDING',(0,0),(-1,-1),3*mm),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story += [mt, Spacer(1, 3*mm)]

    story.extend(_section('1. Identitas dan Target Siklus', styles['section']))
    identity = [
        ['Nama Siklus', cycle.name, 'Periode', f'{_date(cycle.start_date)} – {_date(period_end)}'],
        ['Durasi Target', f'{cycle.target_duration_days} hari', 'Durasi Aktual', f'{metrics["duration_days"]} hari'],
        ['Target DOC', cycle.target_doc, 'Target Size', _n(cycle.target_size,2)],
        ['Target Produksi', f'{_n(cycle.target_biomass_ton,2)} ton', 'Target SR / FCR', f'{_n(cycle.target_sr_percent,2)}% / {_n(cycle.target_fcr,2)}'],
        ['Target ADG', f'{_n(cycle.target_adg,3)} g/hari', 'Target Biaya', _rp(cycle.target_cost)],
        ['Harga Jual Estimasi', _rp(cycle.estimated_price_per_kg), 'Target Pendapatan', _rp(cycle.target_revenue)],
    ]
    it = Table([[ _p(v, styles['td']) for v in r] for r in identity], colWidths=[35*mm,58*mm,35*mm,doc.width-128*mm])
    it.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),light),('GRID',(0,0),(-1,-1),0.35,border),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),2.5*mm)]))
    story.append(it)

    # Rekap produksi per kolam, semua kolam yang pernah muncul dalam data siklus.
    pond_rows = [[r['pond_name'], _n(r['seed_count'],0), _n(r['harvest_total_kg'],2), r['harvest_count'], _date(r['last_sampling_date']), _n(r['last_sampling_doc'],0), _n(r['abw_g'],2), _n(r['size'],2), _n(r['adg'],3), _n(r['fcr'],3), f'{_n(r["sr_index"],2)}%', _n(r['biomass_fr_kg'],2), _n(r['biomass_index_kg'],2)] for r in metrics['pond_rows']]
    _detail_table(story, '2. Rekap Produksi per Kolam', ['Kolam','Tebar','Panen kg','Jml Panen','Sampling Akhir','DOC','ABW g','Size','ADG','FCR','SR','Bio FR kg','Bio Index kg'], pond_rows, styles,
                  widths=[25*mm,19*mm,21*mm,15*mm,24*mm,16*mm,17*mm,16*mm,17*mm,17*mm,18*mm,23*mm,25*mm])

    # KPI.
    kpi_rows = [
        ['Total Tebar', _n(metrics['total_stocking'],0), 'Total Panen', f'{_n(metrics["total_harvest_kg"],2)} kg', 'Pakan', f'{_n(metrics["total_feed_kg"],2)} kg'],
        ['ABW Akhir Rata-rata', f'{_n(metrics["average_abw_g"],2)} g', 'ADG Rata-rata', f'{_n(metrics["average_adg"],3)} g/hari', 'FCR Rata-rata', _n(metrics['average_fcr'],3)],
        ['SR Index Rata-rata', f'{_n(metrics["average_sr_index"],2)}%', 'Mortalitas Siphon', f'{_n(metrics["mortality_total"],0)} ekor', 'Sampling', metrics['sampling_count']],
        ['Cek Anco', metrics['anco_count'], 'Parameter Harian', metrics['parameter_count'], 'Siphon', metrics['siphon_count']],
    ]
    _detail_table(story, '3. KPI Produksi dan Kelengkapan Pencatatan', ['Indikator','Nilai','Indikator','Nilai','Indikator','Nilai'], kpi_rows, styles,
                  widths=[32*mm,45*mm,32*mm,45*mm,32*mm,doc.width-186*mm])

    # Detail operasional lengkap.
    stock_rows = [[_date(o.date), o.pond.name, _n(o.seed_count,0), o.hatchery, o.notes] for o in stocking]
    _detail_table(story, '4. Data Tebar / Stocking (Seluruh Record)', ['Tanggal','Kolam','Jumlah Tebar','Hatchery','Catatan'], stock_rows, styles)

    sampling_rows = [[_date(o.date), o.pond.name, o.doc, _n(o.sample_weight_g,2), o.sample_count, _n(o.abw_last_g,2), _n(o.abw_g,2), _n(o.abw_target_g,2), _n(o.target_size,2), _n(o.size,2), _n(o.adg_weekly,3), _n(o.adg_cumulative,3), f'{_n(o.estimated_sr,2)}%', f'{_n(o.sr_index_percent,2)}%', _n(o.biomass_kg,2), _n(o.biomass_index_kg,2), _n(o.fcr,3), o.population, o.population_index, _n(o.cumulative_feed_kg,2), _n(o.daily_feed_kg,2), f'{_n(o.fr_percent,2)}%', _n(o.index_score,3), _txt(o.harvest_estimation,80)] for o in sampling]
    _detail_table(story, '5. Data Sampling Lengkap (Semua Sampling)', ['Tanggal','Kolam','DOC','Berat Sampel g','N Sampel','ABW Last','ABW','ABW Target','Target Size','Size','ADG 7h','ADG Cum','SR FR','SR Index','Bio FR','Bio Index','FCR','Pop FR','Pop Index','Pakan Kumulatif','Pakan Harian','FR%','Index','Estimasi Panen'], sampling_rows, styles,
                  widths=[doc.width * w / 437 for w in [18,23,13,19,15,16,16,18,18,16,17,17,17,18,19,20,16,18,18,22,18,15,16,34]])

    daily_rows = [[_date(o.date), o.pond.name, o.doc, o.feed_code, _n(o.daily_feed_kg,2), _n(o.water_in_cm,2), o.weather, o.treatment, o.notes] for o in daily]
    _detail_table(story, '6. Data Harian Kolam (Semua Record)', ['Tanggal','Kolam','DOC','Kode Pakan','Pakan kg','Air Masuk cm','Cuaca','Treatment','Catatan'], daily_rows, styles)

    param_rows = [[_date(o.date), o.pond.name, o.doc, o.feed_code, _n(o.water_in_cm,2), o.weather, _n(o.water_level_morning_cm if o.water_level_morning_cm is not None else o.water_level_cm,2), _n(o.water_level_evening_cm if o.water_level_evening_cm is not None else o.water_level_cm,2), _n(o.temperature,2), _n(o.ph_morning,2), _n(o.ph_evening,2), _n(o.do_morning,2), _n(o.do_night,2), _n(o.salinity,2), _n(o.alkalinity,2), _n(o.transparency_morning if o.transparency_morning is not None else o.transparency,2), _n(o.transparency_evening if o.transparency_evening is not None else o.transparency,2), _n(o.feed_kg,2), o.mortality, o.water_color_morning or o.water_color_evening or o.water_color, _txt(o.ai_recommendation,120), _txt(o.notes,100)] for o in params]
    _detail_table(story, '7. Parameter Air dan Lingkungan Harian (Semua Record)', ['Tanggal','Kolam','DOC','Kode Pakan','Air Masuk','Cuaca','Level Pagi','Level Sore','Suhu','pH Pagi','pH Sore','DO Pagi','DO Malam','Salinitas','Alkalinitas','Transparansi Pagi','Transparansi Sore','Pakan','Mortalitas','Warna Air','Rekomendasi AI','Catatan'], param_rows, styles)

    anco_rows = [[_date(o.date), o.pond.name, o.doc, o.feed_code, _n(o.daily_feed_kg,2), o.anco1_morning, o.anco2_morning, o.anco1_noon, o.anco2_noon, o.anco1_evening, o.anco2_evening, o.appetite_status, _txt(o.recommendation,120), _txt(o.notes,100)] for o in anco]
    _detail_table(story, '8. Cek Anco Harian (Semua Record)', ['Tanggal','Kolam','DOC','Kode Pakan','Pakan kg','A1 Pagi','A2 Pagi','A1 Siang','A2 Siang','A1 Sore','A2 Sore','Nafsu Makan','Rekomendasi','Catatan'], anco_rows, styles)

    siphon_rows = [[_date(o.date), o.pond.name, o.doc, o.dead_count, o.live_count, o.daily_total, o.accumulated_total, o.health_indicator, getattr(o.technician, 'username', '-') if o.technician else '-', _txt(o.notes,100)] for o in siphon]
    _detail_table(story, '9. Data Siphon dan Mortalitas (Semua Record)', ['Tanggal','Kolam','DOC','Mati','Hidup','Total Harian','Akumulasi','Indikator Kesehatan','Teknisi','Catatan'], siphon_rows, styles)

    treatment_rows = [[_date(o.date), o.pond.name, o.name, o.dose, o.notes] for o in treatments]
    _detail_table(story, '10. Treatment / Perlakuan (Semua Record)', ['Tanggal','Kolam','Treatment','Dosis','Catatan'], treatment_rows, styles)

    feed_rows = [[_date(o.date), o.pond.name, o.feed_name, _n(o.quantity_kg,2)] for o in feedlogs]
    _detail_table(story, '11. Log Pakan (Semua Record)', ['Tanggal','Kolam','Nama Pakan','Jumlah kg'], feed_rows, styles)

    harvest_rows = [[_date(o.date), o.pond.name, o.harvest_type, o.size_text, _n(o.total_kg,2), o.notes] for o in harvests]
    _detail_table(story, '12. Data Panen (Semua Record)', ['Tanggal','Kolam','Jenis','Size','Berat kg','Catatan'], harvest_rows, styles)

    # Penjualan dan item.
    sale_rows = []
    for o in sale_all:
        customer = o.customer.name if o.customer else '-'
        sale_rows.append([_date(o.date), o.invoice_no, customer, _n(o.total_kg,2), _rp(o.total_amount), o.payment_method, o.status, _rp(o.cash_amount), _rp(o.transfer_amount), _rp(o.qris_amount), _rp(o.other_payment_amount), _date(o.paid_at), _txt(o.notes,80)])
    _detail_table(story, '13. Penjualan / Invoice (Semua Record)', ['Tanggal','Invoice','Pelanggan','Kg','Total','Metode','Status','Tunai','Transfer','QRIS','Lainnya','Lunas','Catatan'], sale_rows, styles)

    item_rows = []
    for sale in sale_all:
        for item in sale.items.all():
            item_rows.append([sale.invoice_no, _date(sale.date), item.size_text, _n(item.weight_kg,2), _rp(item.price_per_kg), _rp(item.subtotal), item.harvest.pond.name if item.harvest and item.harvest.pond else '-'])
    _detail_table(story, '14. Rincian Item Penjualan (Semua Item)', ['Invoice','Tanggal','Size','Berat kg','Harga/kg','Subtotal','Kolam Panen'], item_rows, styles)

    # Keuangan.
    expense_rows = [[_date(o.date), o.pond.name if o.pond else '-', o.category, o.name, _rp(o.amount), o.payment_method, 'Ya' if o.is_fiscal_deductible else 'Tidak', 'Kapitalisasi' if o.is_capital_expenditure else 'Beban', o.fixed_asset.name if o.fixed_asset else '-', o.document_number, _txt(o.notes,100)] for o in expenses]
    _detail_table(story, '15. Pengeluaran Operasional dan Kapitalisasi (Semua Record)', ['Tanggal','Kolam','Kategori','Nama','Jumlah','Metode','Fiskal','Jenis','Aset Terkait','No. Bukti','Catatan'], expense_rows, styles)

    other_rows = [[_date(o.date), o.document_number, o.revenue_type, o.description, o.customer, _rp(o.gross_amount), _rp(o.tax_amount), o.payment_method, _txt(o.notes,100)] for o in other_revenues]
    _detail_table(story, '16. Pendapatan Lain-lain (Semua Record)', ['Tanggal','No. Bukti','Jenis','Uraian','Pelanggan','Bruto','Pajak','Metode','Catatan'], other_rows, styles)

    trade_rows = []
    for t in trades:
        trade_rows.append([t.get_account_type_display(), _date(t.transaction_date), _date(t.due_date), t.document_number, t.partner_name, t.description, _rp(t.original_amount), _rp(t.paid_amount), _rp(t.outstanding_amount), t.payment_status, 'Ya' if t.is_overdue else 'Tidak'])
    _detail_table(story, '17. Piutang dan Utang Siklus (Semua Record)', ['Jenis','Tanggal','Jatuh Tempo','No. Dokumen','Pihak','Uraian','Nilai Awal','Terbayar','Sisa','Status','Jatuh Tempo'], trade_rows, styles)

    payment_rows = []
    for t in trades:
        for pmt in t.payments.all():
            payment_rows.append([t.get_account_type_display(), t.partner_name, _date(pmt.payment_date), pmt.document_number, _rp(pmt.amount), pmt.payment_method, _txt(pmt.notes,100)])
    _detail_table(story, '18. Pembayaran Piutang / Utang (Semua Record)', ['Jenis','Pihak','Tanggal Bayar','No. Bukti','Jumlah','Metode','Catatan'], payment_rows, styles)

    # Rekap finansial.
    category_rows = [[r['category'], _rp(r['total']), f'{(_d(r["total"])/_d(expense_cash)*100):.2f}%'.replace('.', ',') if expense_cash else '0,00%'] for r in pl['grouped']]
    category_rows.append(['TOTAL BEBAN MENURUT MODUL', _rp(pl['expense_total']), '100,00%'])
    _detail_table(story, '19. Rekap Laba/Rugi Siklus', ['Komponen','Jumlah','Proporsi'], [
        ['Penjualan valid', _rp(pl['sales_revenue']), 'Pendapatan utama'],
        ['Pendapatan lain-lain', _rp(pl['other_revenue']), 'Pendapatan tambahan'],
        ['Total pendapatan', _rp(pl['revenue']), ''],
        ['Beban operasional sebelum penyusutan', _rp(pl['operating_expense_before_depreciation']), ''],
        ['Penyusutan', _rp(pl['depreciation_total']), 'Engine penyusutan aset'],
        ['Total beban', _rp(pl['expense_total']), ''],
        ['Laba / rugi', _rp(pl['profit']), ''],
    ], styles, widths=[75*mm,65*mm,doc.width-140*mm])
    _detail_table(story, '20. Komposisi Biaya per Kategori', ['Kategori','Jumlah','Proporsi'], category_rows, styles, widths=[80*mm,65*mm,doc.width-145*mm])

    financial_summary = [
        ['Omzet penjualan valid', _rp(total_sale_amount), 'Kg terjual', f'{_n(total_sale_kg,2)} kg'],
        ['Pendapatan lain-lain', _rp(total_other_revenue), 'Jumlah invoice', sales.count()],
        ['Beban operasional kas', _rp(expense_cash), 'Pembelian aset/kapitalisasi', _rp(capital_expense)],
        ['Piutang awal', _rp(receivable_original), 'Piutang tersisa', _rp(receivable_outstanding)],
        ['Utang awal', _rp(payable_original), 'Utang tersisa', _rp(payable_outstanding)],
        ['Total pembayaran utang/piutang', _rp(total_trade_paid), 'Laba/rugi modul', _rp(pl['profit'])],
    ]
    _detail_table(story, '21. Posisi Keuangan Terkait Siklus', ['Indikator','Nilai','Indikator','Nilai'], financial_summary, styles,
                  widths=[55*mm,65*mm,55*mm,doc.width-175*mm])

    # Dokumen pendukung: semua metadata attachment yang terkait transaksi siklus.
    doc_rows = []
    for e in expenses:
        for d in e.documents.all():
            doc_rows.append(['Pengeluaran', e.name, d.original_name or d.file.name, d.description, _date(d.uploaded_at.date() if d.uploaded_at else None)])
    for s in sale_all:
        for d in s.documents.all():
            doc_rows.append(['Penjualan', s.invoice_no, d.document_type, d.description, _date(d.uploaded_at.date() if d.uploaded_at else None)])
    for t in trades:
        for d in t.documents.all():
            doc_rows.append(['Utang/Piutang', t.document_number or t.partner_name, d.original_name or d.file.name, d.description, _date(d.uploaded_at.date() if d.uploaded_at else None)])
    _detail_table(story, '22. Daftar Dokumen Pendukung yang Terhubung', ['Sumber','Referensi','Nama/Jenis Dokumen','Keterangan','Tanggal Upload'], doc_rows, styles)

    story.extend(_section('23. Catatan Siklus dan Integritas Arsip', styles['section']))
    note = cycle.notes or '-'
    story.append(_p(f'<b>Catatan siklus:</b> {note}', styles['small']))
    story.append(Spacer(1, 2*mm))
    story.append(_p(
        f'Laporan ini dibuat otomatis pada {timezone.localtime().strftime("%d/%m/%Y %H:%M WIB")}. '
        'Seluruh tabel operasional dan transaksi pada bagian lampiran difilter berdasarkan siklus yang dipilih. '
        'File asli dokumen pendukung tidak disalin ke PDF; yang ditampilkan adalah metadata dokumen yang tersimpan pada aplikasi.',
        styles['muted']))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="laporan_akhir_lengkap_{_safe_name(cycle.name)}.pdf"'
    return response
