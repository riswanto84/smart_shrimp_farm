from datetime import date
from decimal import Decimal

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def get_date_range(request):
    """Read ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD, with safe parsing."""
    date_from = parse_date(request.GET.get("date_from") or "")
    date_to = parse_date(request.GET.get("date_to") or "")
    return date_from, date_to


def filter_by_date_range(qs, field_name, date_from=None, date_to=None, is_datetime=False):
    """Apply date range filters to DateField or DateTimeField querysets."""
    if date_from:
        lookup = f"{field_name}__date__gte" if is_datetime else f"{field_name}__gte"
        qs = qs.filter(**{lookup: date_from})
    if date_to:
        lookup = f"{field_name}__date__lte" if is_datetime else f"{field_name}__lte"
        qs = qs.filter(**{lookup: date_to})
    return qs


def format_date_range(date_from, date_to):
    if date_from and date_to:
        return f"{date_from.strftime('%d/%m/%Y')} s.d. {date_to.strftime('%d/%m/%Y')}"
    if date_from:
        return f"Mulai {date_from.strftime('%d/%m/%Y')}"
    if date_to:
        return f"Sampai {date_to.strftime('%d/%m/%Y')}"
    return "Semua tanggal"


def rupiah(value):
    value = value or 0
    try:
        value = Decimal(value)
    except Exception:
        value = Decimal(0)
    return "Rp {:,.0f}".format(value).replace(",", ".")


def export_excel(filename, title, subtitle, headers, rows, total_rows=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Laporan"

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers), 2))
    ws.cell(row=1, column=1).value = title
    ws.cell(row=1, column=1).font = Font(size=15, bold=True, color="FFFFFF")
    ws.cell(row=1, column=1).fill = PatternFill("solid", fgColor="0B3A75")
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(len(headers), 2))
    ws.cell(row=2, column=1).value = subtitle
    ws.cell(row=2, column=1).alignment = Alignment(horizontal="center")

    start_row = 4
    header_fill = PatternFill("solid", fgColor="1E73E8")
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    for row_idx, row in enumerate(rows, start=start_row + 1):
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = border
            if isinstance(value, (int, float, Decimal)):
                cell.number_format = '#,##0.00'

    if total_rows:
        row_idx = start_row + 1 + len(rows) + 1
        for total in total_rows:
            for col_idx, value in enumerate(total, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="EAF2FF")
                cell.border = border
                if isinstance(value, (int, float, Decimal)):
                    cell.number_format = '#,##0.00'
            row_idx += 1

    ws.freeze_panes = "A5"
    for col_idx in range(1, len(headers) + 1):
        max_len = 10
        for row_idx in range(1, ws.max_row + 1):
            value = ws.cell(row=row_idx, column=col_idx).value
            if value is not None:
                max_len = max(max_len, min(len(str(value)) + 2, 35))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response


def export_pdf(filename, title, subtitle, headers, rows, total_rows=None):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Paragraph(subtitle, styles["Normal"]))
    elements.append(Spacer(1, 12))

    data = [headers]
    for row in rows:
        data.append(["" if v is None else str(v) for v in row])
    if total_rows:
        data.append(["" for _ in headers])
        for total in total_rows:
            data.append(["" if v is None else str(v) for v in total])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3A75")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E2F3")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFF")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    doc.build(elements)
    return response
