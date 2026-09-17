from decimal import Decimal, InvalidOperation


def parse_rupiah(value):
    """Terima input uang seperti 70000, 70.000, Rp 70.000 lalu menjadi Decimal(70000)."""
    if value is None:
        return Decimal('0')
    cleaned = str(value).strip().replace('Rp', '').replace('rp', '').replace(' ', '')
    # Format Indonesia memakai titik sebagai pemisah ribuan dan koma sebagai desimal.
    cleaned = cleaned.replace('.', '').replace(',', '.')
    if cleaned in ('', '-', '.'):
        return Decimal('0')
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal('0')
