from pathlib import Path
import re
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from core.reporting import rupiah

BUSINESS_NAME = 'UDANG EMAS NUSANTARA'
TAGLINE = 'Dari tambak nusantara untuk kualitas dunia'
ADDRESS_LINES = [
    'Jalan Pantai Mekar, Kec. Muara Gembong,',
    'Kabupaten Bekasi, Jawa Barat 17730',
]
PHONE = '081219142796'
INSTAGRAM = '@udang.emas.nusantara'
TIKTOK = 'udang.emas.nusantara'


def _money_plain(value):
    return rupiah(value).replace('Rp ', '')


def _safe_text(value, default='-'):
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def safe_invoice_filename(invoice_no):
    """Ubah nomor nota menjadi nama file aman.

    Nomor nota sering memakai garis miring, contoh INV/2026/06/0001.
    Jika dipakai langsung sebagai nama file, Python akan menganggapnya sebagai folder
    media/invoices/INV/2026/06/0001.pdf dan bisa memicu FileNotFoundError.
    """
    text = _safe_text(invoice_no, 'invoice')
    text = re.sub(r'[^A-Za-z0-9_.-]+', '-', text).strip('-')
    return text or 'invoice'


def _fit_text(c, text, x, y, max_width, font='Courier', size=8):
    text = _safe_text(text, '')
    c.setFont(font, size)
    if c.stringWidth(text, font, size) <= max_width:
        c.drawString(x, y, text)
        return
    ell = '...'
    while text and c.stringWidth(text + ell, font, size) > max_width:
        text = text[:-1]
    c.drawString(x, y, text + ell)


def _line(c, y, width, margin, dashed=True):
    if dashed:
        c.setDash(3, 2)
    else:
        c.setDash()
    c.line(margin, y, width - margin, y)
    c.setDash()


def _wrap_text(text, max_chars=18):
    """Wrap sederhana untuk kolom item nota thermal agar tidak menabrak Qty/Harga/Total."""
    words = _safe_text(text, '').split()
    lines, line = [], ''
    for word in words:
        candidate = f'{line} {word}'.strip()
        if len(candidate) > max_chars and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines or ['-']


def _draw_centered_icon_text(c, icon_path, text, y, width, size=3.2 * mm):
    c.setFont('Courier-Bold', 7)
    text_width = c.stringWidth(text, 'Courier-Bold', 7)
    gap = 2 * mm
    total_w = size + gap + text_width
    x = (width - total_w) / 2
    if icon_path.exists():
        c.drawImage(ImageReader(str(icon_path)), x, y - size + 1, width=size, height=size, mask='auto')
        c.drawString(x + size + gap, y - size + 2, text)
    else:
        c.drawCentredString(width / 2, y - size + 2, text)


def build_invoice_pdf(sale):
    """Membuat PDF nota ukuran thermal 80 mm, cocok untuk printer POS."""
    out = Path(settings.MEDIA_ROOT) / 'invoices'
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{safe_invoice_filename(sale.invoice_no)}.pdf'
    path.parent.mkdir(parents=True, exist_ok=True)

    items = list(sale.items.all())
    width = 80 * mm
    # tinggi dinamis agar nota tidak terpotong; minimal 220 mm
    height = max(220 * mm, (188 + len(items) * 19) * mm)
    margin = 6 * mm
    right = width - margin
    y = height - 8 * mm

    c = canvas.Canvas(str(path), pagesize=(width, height))
    c.setTitle(f'Nota {sale.invoice_no}')
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)

    static_img = Path(settings.BASE_DIR) / 'static' / 'img'

    # Logo thermal: simbol udang menghadap kanan dari logo Udang Emas Nusantara.
    logo = static_img / 'logo_uen_thermal.png'
    if logo.exists():
        logo_w = 34 * mm
        logo_h = 20 * mm
        c.drawImage(ImageReader(str(logo)), (width - logo_w) / 2, y - logo_h, width=logo_w, height=logo_h, mask='auto', preserveAspectRatio=True)
        y -= logo_h + 3 * mm

    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(width / 2, y, BUSINESS_NAME)
    y -= 5 * mm
    c.setFont('Helvetica', 7.6)
    c.drawCentredString(width / 2, y, TAGLINE)
    y -= 5 * mm
    c.setFont('Courier', 8)
    for line in ADDRESS_LINES:
        c.drawCentredString(width / 2, y, line)
        y -= 4 * mm
    c.drawCentredString(width / 2, y, f'Telp. {PHONE}')
    y -= 5 * mm

    _line(c, y, width, margin)
    y -= 6 * mm

    sale_date = timezone.localtime(sale.date).strftime('%d %b %Y %H:%M') if sale.date else '-'
    cashier = sale.cashier.get_full_name() or sale.cashier.username if sale.cashier else '-'
    meta = [
        ('No. Nota', sale.invoice_no),
        ('Tanggal', sale_date),
        ('Kasir', cashier),
        ('Pelanggan', sale.customer.name if sale.customer else 'Umum'),
        ('No. HP', sale.customer.phone if sale.customer else '-'),
        ('Metode Bayar', sale.payment_method),
    ]
    c.setFont('Courier', 8)
    for label, value in meta:
        c.drawString(margin, y, label)
        c.drawString(margin + 28 * mm, y, ':')
        _fit_text(c, value, margin + 31 * mm, y, width - (margin + 31 * mm) - margin, 'Courier', 8)
        y -= 5 * mm

    y -= 1 * mm
    _line(c, y, width, margin)
    y -= 5 * mm

    item_x = margin
    qty_x = margin + 43 * mm
    price_x = margin + 57 * mm
    total_x = right
    item_max_width = qty_x - item_x - 2 * mm

    c.setFont('Courier-Bold', 8)
    c.drawString(item_x, y, 'ITEM')
    c.drawRightString(qty_x, y, 'QTY')
    c.drawRightString(price_x, y, 'HARGA')
    c.drawRightString(total_x, y, 'TOTAL')
    y -= 2.5 * mm
    _line(c, y, width, margin, dashed=False)
    y -= 5 * mm

    c.setFont('Courier', 8)
    for it in items:
        item_lines = _wrap_text('Udang Vaname Fresh', max_chars=17)
        item_lines.append(f'Size {it.size_text or "-"}')
        first_line_y = y
        for idx, line in enumerate(item_lines):
            if idx == 0:
                _fit_text(c, line, item_x, y, item_max_width, 'Courier', 8)
            else:
                _fit_text(c, line, item_x, y, item_max_width, 'Courier', 8)
            y -= 4 * mm
        c.drawRightString(qty_x, first_line_y, f'{it.weight_kg} kg')
        c.drawRightString(price_x, first_line_y, _money_plain(it.price_per_kg))
        c.drawRightString(total_x, first_line_y, _money_plain(it.subtotal))
        y -= 4 * mm

    _line(c, y, width, margin, dashed=False)
    y -= 7 * mm

    c.setFont('Courier', 8)
    c.drawRightString(margin + 47 * mm, y, 'TOTAL KG')
    c.drawRightString(right, y, f'{sale.total_kg} kg')
    y -= 6 * mm

    _line(c, y, width, margin)
    y -= 7 * mm
    c.setFont('Helvetica-Bold', 14)
    c.drawString(margin, y, 'TOTAL')
    c.drawRightString(right, y, _money_plain(sale.total_amount))
    y -= 5 * mm
    _line(c, y, width, margin, dashed=False)
    y -= 7 * mm

    c.setFont('Courier', 8)
    c.drawString(margin, y, 'STATUS')
    c.drawRightString(right, y, sale.status)
    y -= 6 * mm

    _line(c, y, width, margin)
    y -= 5 * mm
    c.setFont('Courier-Bold', 8)
    c.drawString(margin, y, 'CATATAN:')
    y -= 4 * mm
    c.setFont('Courier', 8)
    note = sale.notes or 'Pengiriman menggunakan mobil berpendingin. Terima kasih atas kepercayaannya.'
    words, line = note.split(), ''
    max_chars = 42
    for word in words:
        if len(line + ' ' + word) > max_chars:
            c.drawString(margin, y, line.strip())
            y -= 4 * mm
            line = word
        else:
            line = f'{line} {word}'
    if line:
        c.drawString(margin, y, line.strip())
        y -= 5 * mm

    _line(c, y, width, margin)
    y -= 6 * mm
    c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(width / 2, y, '■ Terima kasih telah berbelanja ■')
    y -= 5 * mm
    c.setFont('Courier', 7)
    c.drawCentredString(width / 2, y, 'Barang yang sudah dibeli tidak dapat ditukar')
    y -= 3.5 * mm
    c.drawCentredString(width / 2, y, 'kecuali ada kesalahan input.')
    y -= 6 * mm

    _draw_centered_icon_text(c, static_img / 'icon_instagram.png', f'IG: {INSTAGRAM}', y, width)
    y -= 5 * mm
    _draw_centered_icon_text(c, static_img / 'icon_tiktok.png', f'TikTok: {TIKTOK}', y, width)

    c.showPage()
    c.save()
    return str(path)
