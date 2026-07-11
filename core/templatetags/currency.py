from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django import template

register = template.Library()


def _to_decimal(value):
    if value is None or value == '':
        return Decimal('0')
    try:
        # Terima input/hasil dengan format Indonesia maupun standar Python.
        text = str(value).strip().replace('Rp', '').replace(' ', '')
        if ',' in text and '.' in text:
            # Contoh 1.234,56 -> 1234.56
            text = text.replace('.', '').replace(',', '.')
        elif ',' in text:
            # Contoh 1234,56 -> 1234.56
            text = text.replace(',', '.')
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


def _format_id_number(value, decimals=2, strip_zero=True):
    amount = _to_decimal(value)
    sign = '-' if amount < 0 else ''
    amount = abs(amount)
    try:
        decimals = int(decimals)
    except Exception:
        decimals = 2
    decimals = max(0, min(decimals, 2))

    q = Decimal('1') if decimals == 0 else Decimal('1').scaleb(-decimals)
    amount = amount.quantize(q, rounding=ROUND_HALF_UP)
    whole = int(amount)
    fraction = amount - Decimal(whole)
    whole_text = f"{whole:,}".replace(',', '.')

    if decimals == 0:
        return f"{sign}{whole_text}"

    frac_text = f"{fraction:.{decimals}f}".split('.')[1]
    if strip_zero:
        frac_text = frac_text.rstrip('0')
    if frac_text:
        return f"{sign}{whole_text},{frac_text}"
    return f"{sign}{whole_text}"


@register.filter(name='angka')
def angka(value, decimals=2):
    """Format angka Indonesia: 1234567.891 -> 1.234.567,89. Maksimal 2 desimal."""
    return _format_id_number(value, decimals=decimals, strip_zero=True)


@register.filter(name='angka0')
def angka0(value):
    return _format_id_number(value, decimals=0, strip_zero=True)


@register.filter(name='angka2')
def angka2(value):
    return _format_id_number(value, decimals=2, strip_zero=True)


@register.filter(name='rupiah')
def rupiah(value):
    """Format Rupiah Indonesia dengan maksimal 2 desimal bila diperlukan."""
    return f"Rp {_format_id_number(value, decimals=2, strip_zero=True)}"


@register.filter(name='ribuan')
def ribuan(value):
    """Format angka ribuan Indonesia tanpa simbol mata uang, tanpa desimal."""
    return _format_id_number(value, decimals=0, strip_zero=True)


@register.filter(name='desimal3')
def desimal3(value):
    """Format angka Indonesia tepat 3 digit desimal: 2.47 -> 2,470."""
    amount = _to_decimal(value)
    sign = '-' if amount < 0 else ''
    amount = abs(amount).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    whole = int(amount)
    fraction = amount - Decimal(whole)
    whole_text = f"{whole:,}".replace(',', '.')
    frac_text = f"{fraction:.3f}".split('.')[1]
    return f"{sign}{whole_text},{frac_text}"
