from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


def _to_decimal(value):
    if value is None or value == '':
        return Decimal('0')
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


@register.filter(name='rupiah')
def rupiah(value):
    """Format angka menjadi Rupiah Indonesia: Rp 1.250.000."""
    amount = _to_decimal(value)
    sign = '-' if amount < 0 else ''
    amount = abs(amount)
    whole = int(amount.quantize(Decimal('1')))
    return f"{sign}Rp {whole:,}".replace(',', '.')


@register.filter(name='ribuan')
def ribuan(value):
    """Format angka ribuan Indonesia tanpa simbol mata uang."""
    amount = _to_decimal(value)
    sign = '-' if amount < 0 else ''
    amount = abs(amount)
    whole = int(amount.quantize(Decimal('1')))
    return f"{sign}{whole:,}".replace(',', '.')
