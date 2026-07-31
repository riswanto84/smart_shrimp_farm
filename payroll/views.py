from decimal import Decimal
from io import BytesIO
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.urls import reverse
from django.core import signing
from django.utils.http import urlencode
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from accounts.rbac import permission_required
from finance.models import OperationalExpense
from .forms import EmployeeForm, PayrollPeriodForm, PayrollRecordForm
from .models import Employee, PayrollPeriod, PayrollRecord


def _sync_expense(record):
    if record.payment_status != 'paid' or not record.payment_date:
        return
    defaults = {
        'date': record.payment_date,
        'category': 'Tenaga Kerja',
        'name': f'Gaji {record.employee.name} - {record.period.name}',
        'amount': record.net_salary,
        'payment_method': record.payment_method,
        'notes': (
            f'Dibuat otomatis dari modul penggajian. Periode {record.period.start_date:%d/%m/%Y} '
            f's.d. {record.period.end_date:%d/%m/%Y}.'
            + (f' Keterangan: {record.notes}' if record.notes else '')
            + (f' Catatan: {record.catatan}' if record.catatan else '')
        ),
        'is_fiscal_deductible': True,
        'payment_status': 'paid',
    }
    if record.expense_id:
        for key, value in defaults.items():
            setattr(record.expense, key, value)
        record.expense.save()
    else:
        expense = OperationalExpense.objects.create(**defaults)
        PayrollRecord.objects.filter(pk=record.pk).update(expense=expense)
        record.expense = expense


@permission_required('payroll.view')
def dashboard(request):
    today = timezone.localdate()
    current_year = today.year
    records = PayrollRecord.objects.filter(period__start_date__year=current_year)
    context = {
        'employee_count': Employee.objects.filter(employment_status='active').count(),
        'period_count': PayrollPeriod.objects.filter(start_date__year=current_year).count(),
        'total_net': records.aggregate(v=Sum('net_salary'))['v'] or Decimal('0'),
        'total_paid': records.aggregate(v=Sum('amount_paid'))['v'] or Decimal('0'),
        'total_outstanding': sum((r.outstanding_amount for r in records), Decimal('0')),
        'recent_periods': PayrollPeriod.objects.all()[:6],
        'unpaid_records': PayrollRecord.objects.exclude(payment_status='paid').select_related('employee', 'period')[:8],
    }
    return render(request, 'payroll/dashboard.html', context)


@permission_required('payroll.manage')
def employee_list(request):
    q = request.GET.get('q', '').strip()
    employees = Employee.objects.all()
    if q:
        employees = employees.filter(Q(employee_code__icontains=q) | Q(name__icontains=q) | Q(position__icontains=q))
    return render(request, 'payroll/employee_list.html', {'employees': employees, 'q': q})


@permission_required('payroll.manage')
def employee_form(request, pk=None):
    obj = get_object_or_404(Employee, pk=pk) if pk else None
    form = EmployeeForm(request.POST or None, instance=obj)
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-control')
    for name in ('employment_status', 'pay_type'):
        form.fields[name].widget.attrs['class'] = 'form-select'
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Data karyawan berhasil disimpan.')
        return redirect('payroll:employee_list')
    return render(request, 'payroll/form.html', {'form': form, 'title': 'Edit Karyawan' if obj else 'Tambah Karyawan', 'back_url': '/payroll/employees/'})


@permission_required('payroll.view')
def period_list(request):
    periods = PayrollPeriod.objects.all()
    return render(request, 'payroll/period_list.html', {'periods': periods})


@permission_required('payroll.manage')
def period_form(request, pk=None):
    obj = get_object_or_404(PayrollPeriod, pk=pk) if pk else None
    form = PayrollPeriodForm(request.POST or None, instance=obj)
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-control')
    form.fields['status'].widget.attrs['class'] = 'form-select'
    if request.method == 'POST' and form.is_valid():
        period = form.save(commit=False)
        if not period.pk:
            period.created_by = request.user
        period.save()
        messages.success(request, 'Periode penggajian berhasil disimpan.')
        return redirect('payroll:period_detail', pk=period.pk)
    return render(request, 'payroll/form.html', {'form': form, 'title': 'Edit Periode Penggajian' if obj else 'Tambah Periode Penggajian', 'back_url': '/payroll/periods/'})


@permission_required('payroll.view')
def period_detail(request, pk):
    period = get_object_or_404(PayrollPeriod, pk=pk)
    records = period.records.select_related('employee')
    return render(request, 'payroll/period_detail.html', {'period': period, 'records': records})


@permission_required('payroll.manage')
def record_form(request, period_pk=None, pk=None):
    obj = get_object_or_404(PayrollRecord, pk=pk) if pk else None
    period = obj.period if obj else get_object_or_404(PayrollPeriod, pk=period_pk)
    form = PayrollRecordForm(request.POST or None, instance=obj, period=period)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        record.period = period
        employee = record.employee
        if not obj and record.base_salary == 0:
            record.base_salary = employee.base_salary if employee.pay_type == 'monthly' else employee.daily_rate * record.work_days
        record.save()
        _sync_expense(record)
        messages.success(request, 'Perhitungan gaji berhasil disimpan.')
        return redirect('payroll:period_detail', pk=period.pk)
    if not obj and request.method != 'POST':
        form.fields['base_salary'].help_text = 'Boleh dikosongkan/0; sistem mengambil gaji pokok karyawan atau upah harian × hari kerja.'
    return render(request, 'payroll/record_form.html', {'form': form, 'period': period, 'title': 'Edit Gaji Karyawan' if obj else 'Tambah Gaji Karyawan'})


@permission_required('payroll.manage')
def record_delete(request, pk):
    record = get_object_or_404(PayrollRecord, pk=pk)
    period_pk = record.period_id
    if request.method == 'POST':
        if record.expense_id:
            record.expense.delete()
        record.delete()
        messages.success(request, 'Data gaji berhasil dihapus.')
    return redirect('payroll:period_detail', pk=period_pk)


@permission_required('payroll.view')
def salary_slip(request, pk):
    record = get_object_or_404(PayrollRecord.objects.select_related('employee', 'period'), pk=pk)
    return render(request, 'payroll/salary_slip.html', {'record': record})


def _rupiah_pdf(value):
    return 'Rp{:,.0f}'.format(value or Decimal('0')).replace(',', '.')


def _salary_slip_pdf_response(request, record):
    response = HttpResponse(content_type='application/pdf')
    safe_code = ''.join(c for c in record.employee.employee_code if c.isalnum() or c in ('-', '_'))
    filename = f"slip_gaji_{safe_code}_{record.period.start_date:%Y%m}.pdf"
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle('SlipTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=18, leading=22, alignment=TA_CENTER, textColor=colors.HexColor('#0b2d52'))
    center = ParagraphStyle('Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor('#667085'))
    right = ParagraphStyle('Right', parent=styles['Normal'], alignment=TA_RIGHT)
    normal = ParagraphStyle('NormalSlip', parent=styles['Normal'], fontSize=9.5, leading=13)
    section = ParagraphStyle('Section', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#0b2d52'), spaceBefore=8, spaceAfter=5)

    story = [Paragraph('SLIP GAJI KARYAWAN', title), Paragraph('Smart Shrimp Farm · Udang Emas Nusantara', center), Spacer(1, 7*mm)]
    info = [
        ['Nama Karyawan', record.employee.name, 'Periode', record.period.name],
        ['NIK/Kode', record.employee.employee_code, 'Tanggal', f"{record.period.start_date:%d/%m/%Y} s.d. {record.period.end_date:%d/%m/%Y}"],
        ['Jabatan', record.employee.position or '-', 'Status', record.get_payment_status_display()],
        ['Metode', record.get_payment_method_display(), 'Tanggal Bayar', record.payment_date.strftime('%d/%m/%Y') if record.payment_date else '-'],
    ]
    t=Table(info, colWidths=[28*mm, 58*mm, 28*mm, 58*mm])
    t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),9),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,-1),(-1,-1),0.8,colors.HexColor('#d7a823'))]))
    story += [t, Spacer(1, 4*mm), Paragraph('Pendapatan', section)]
    income=[['Gaji Pokok/Upah',_rupiah_pdf(record.base_salary)],['Lembur',_rupiah_pdf(record.overtime_pay)],['Uang Makan',_rupiah_pdf(record.meal_allowance)],['Transportasi',_rupiah_pdf(record.transport_allowance)],['Tunjangan Lain',_rupiah_pdf(record.other_allowance)],['Bonus',_rupiah_pdf(record.bonus)],['GAJI BRUTO',_rupiah_pdf(record.gross_salary)]]
    ti=Table(income,colWidths=[120*mm,52*mm])
    ti.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),9.5),('ALIGN',(1,0),(1,-1),'RIGHT'),('GRID',(0,0),(-1,-2),0.35,colors.HexColor('#e5e7eb')),('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#eef4fb')),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('BOX',(0,0),(-1,-1),0.6,colors.HexColor('#cfd8e3')),('PADDING',(0,0),(-1,-1),6)]))
    story += [ti, Paragraph('Potongan', section)]
    deductions=[['Potongan BPJS',_rupiah_pdf(record.bpjs_deduction)],['Potongan Pajak',_rupiah_pdf(record.tax_deduction)],['Potongan Kasbon',_rupiah_pdf(record.loan_deduction)],['Potongan Lain',_rupiah_pdf(record.other_deduction)],['TOTAL POTONGAN',_rupiah_pdf(record.total_deduction)],['GAJI BERSIH',_rupiah_pdf(record.net_salary)],['JUMLAH DIBAYAR',_rupiah_pdf(record.amount_paid)]]
    td=Table(deductions,colWidths=[120*mm,52*mm])
    td.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),9.5),('ALIGN',(1,0),(1,-1),'RIGHT'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#e5e7eb')),('BACKGROUND',(0,-3),(-1,-3),colors.HexColor('#fff7e0')),('FONTNAME',(0,-3),(-1,-1),'Helvetica-Bold'),('BACKGROUND',(0,-2),(-1,-2),colors.HexColor('#dff4e7')),('BOX',(0,0),(-1,-1),0.6,colors.HexColor('#cfd8e3')),('PADDING',(0,0),(-1,-1),6)]))
    story.append(td)
    if record.notes or record.catatan:
        story.append(Spacer(1,4*mm))
        if record.notes: story += [Paragraph('<b>Keterangan</b>', normal), Paragraph(record.notes.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n','<br/>'), normal)]
        if record.catatan: story += [Spacer(1,2*mm), Paragraph('<b>Catatan</b>', normal), Paragraph(record.catatan.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n','<br/>'), normal)]
    story += [Spacer(1,15*mm), Table([['Penerima','Penanggung Jawab'],['',''],[record.employee.name,'____________________']], colWidths=[86*mm,86*mm], rowHeights=[6*mm,18*mm,7*mm], style=TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,2),(-1,2),'Helvetica-Bold'),('LINEABOVE',(0,2),(-1,2),0.5,colors.black)]))]
    doc.build(story)
    return response


@permission_required('payroll.view')
def salary_slip_pdf(request, pk):
    record = get_object_or_404(PayrollRecord.objects.select_related('employee', 'period'), pk=pk)
    return _salary_slip_pdf_response(request, record)


def salary_slip_pdf_shared(request, token):
    try:
        pk = signing.loads(token, salt='payroll-slip-share', max_age=60 * 60 * 24 * 30)
    except signing.BadSignature:
        return HttpResponse('Tautan slip gaji tidak valid atau sudah kedaluwarsa.', status=403)
    record = get_object_or_404(PayrollRecord.objects.select_related('employee', 'period'), pk=pk)
    return _salary_slip_pdf_response(request, record)


@permission_required('payroll.view')
def salary_slip_whatsapp(request, pk):
    record = get_object_or_404(PayrollRecord.objects.select_related('employee', 'period'), pk=pk)
    token = signing.dumps(record.pk, salt='payroll-slip-share')
    pdf_url = request.build_absolute_uri(reverse('payroll:salary_slip_pdf_shared', args=[token]))
    message = (
        f"Assalamu'alaikum {record.employee.name},\n\n"
        f"Berikut slip gaji periode {record.period.name}.\n"
        f"Gaji bersih: {_rupiah_pdf(record.net_salary)}\n"
        f"Status: {record.get_payment_status_display()}\n\n"
        f"Slip PDF: {pdf_url}\n\n"
        "Terima kasih."
    )
    phone = ''.join(ch for ch in (record.employee.phone or '') if ch.isdigit())
    if phone.startswith('0'):
        phone = '62' + phone[1:]
    elif phone and not phone.startswith('62'):
        phone = '62' + phone
    target = f"https://wa.me/{phone}?{urlencode({'text': message})}" if phone else f"https://wa.me/?{urlencode({'text': message})}"
    return redirect(target)


def _filtered_records(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    employee_id = request.GET.get('employee')
    status = request.GET.get('status')
    qs = PayrollRecord.objects.select_related('employee', 'period').all()
    if start:
        qs = qs.filter(period__end_date__gte=start)
    if end:
        qs = qs.filter(period__start_date__lte=end)
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    if status:
        qs = qs.filter(payment_status=status)
    return qs, start, end, employee_id, status


@permission_required('payroll.view')
def report(request):
    records, start, end, employee_id, status = _filtered_records(request)
    totals = records.aggregate(gross=Sum('gross_salary'), deduction=Sum('total_deduction'), net=Sum('net_salary'), paid=Sum('amount_paid'))
    totals = {k: v or Decimal('0') for k, v in totals.items()}
    totals['outstanding'] = sum((r.outstanding_amount for r in records), Decimal('0'))
    return render(request, 'payroll/report.html', {
        'records': records, 'employees': Employee.objects.all(), 'totals': totals,
        'start': start, 'end': end, 'employee_id': employee_id, 'status': status,
    })


@permission_required('payroll.view')
def report_excel(request):
    records, start, end, employee_id, status = _filtered_records(request)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Laporan Penggajian'
    ws.merge_cells('A1:N1')
    ws['A1'] = 'LAPORAN PENGGAJIAN KARYAWAN'
    ws['A1'].font = Font(size=16, bold=True)
    ws['A1'].alignment = Alignment(horizontal='center')
    headers = ['Periode', 'Kode', 'Nama', 'Jabatan', 'Gaji Pokok', 'Lembur', 'Tunjangan', 'Bonus', 'Potongan', 'Gaji Bersih', 'Dibayar', 'Sisa', 'Status', 'Keterangan']
    ws.append([])
    ws.append(headers)
    for cell in ws[3]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='0B2D55')
    for r in records:
        allowances = r.meal_allowance + r.transport_allowance + r.other_allowance
        ws.append([r.period.name, r.employee.employee_code, r.employee.name, r.employee.position, float(r.base_salary), float(r.overtime_pay), float(allowances), float(r.bonus), float(r.total_deduction), float(r.net_salary), float(r.amount_paid), float(r.outstanding_amount), r.get_payment_status_display(), r.notes or '-'])
    for col in ('E','F','G','H','I','J','K','L'):
        for cell in ws[col][3:]:
            cell.number_format = 'Rp #,##0'
    widths = [22,14,24,20,16,14,16,14,16,17,16,16,18,36]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64+i)].width = width
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="laporan_penggajian.xlsx"'
    return response
