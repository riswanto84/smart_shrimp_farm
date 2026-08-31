from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from django.utils import timezone

from cultivation.models import CultivationCycle
from finance.models import TradeAccount
from finance.services.profit_loss import calculate_profit_loss
from operations.services.biomass import calculate_index_biomass_snapshot
from sales.models import Sale, SaleItem


ZERO = Decimal('0')
TAX_RATE_DEFAULT = Decimal('0.005')


def _decimal(value, default=ZERO):
    try:
        return Decimal(str(value if value is not None else default))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(str(default))


def weighted_average_sale_price(*, cycle=None, as_of=None):
    """Harga jual rata-rata tertimbang dari detail penjualan yang valid."""
    as_of = as_of or timezone.localdate()
    qs = SaleItem.objects.filter(
        sale__date__date__lte=as_of,
        weight_kg__gt=0,
        price_per_kg__gt=0,
    ).exclude(sale__status__in=['Gagal', 'Expired', 'Dibatalkan', 'Refund'])
    if cycle is not None:
        qs = qs.filter(sale__cycle=cycle)

    totals = qs.aggregate(weight=Sum('weight_kg'), amount=Sum('subtotal'))
    weight = _decimal(totals.get('weight'))
    amount = _decimal(totals.get('amount'))
    if weight > 0 and amount > 0:
        return (amount / weight).quantize(Decimal('0.01')), 'Rata-rata tertimbang penjualan aktual'

    # Fallback ke total nota jika instalasi lama belum memiliki SaleItem lengkap.
    sales = Sale.objects.filter(date__date__lte=as_of).exclude(
        status__in=['Gagal', 'Expired', 'Dibatalkan', 'Refund']
    )
    if cycle is not None:
        sales = sales.filter(cycle=cycle)
    sale_totals = sales.aggregate(weight=Sum('total_kg'), amount=Sum('total_amount'))
    weight = _decimal(sale_totals.get('weight'))
    amount = _decimal(sale_totals.get('amount'))
    if weight > 0 and amount > 0:
        return (amount / weight).quantize(Decimal('0.01')), 'Rata-rata omzet ÷ berat penjualan'

    cycle_price = _decimal(getattr(cycle, 'estimated_price_per_kg', ZERO)) if cycle else ZERO
    if cycle_price > 0:
        return cycle_price.quantize(Decimal('0.01')), 'Harga estimasi siklus'
    return ZERO, 'Harga belum tersedia'



def latest_harvest_sale_price(*, cycle=None, as_of=None):
    """Harga jual dari transaksi panen/penjualan paling baru yang valid.

    Jika nota terbaru memiliki beberapa item/size, harga dihitung rata-rata
    tertimbang hanya untuk nota terbaru tersebut. Fallback selanjutnya adalah
    rata-rata penjualan siklus, lalu harga estimasi siklus.
    """
    as_of = as_of or timezone.localdate()
    valid_items = SaleItem.objects.select_related('sale', 'harvest').filter(
        sale__date__date__lte=as_of,
        weight_kg__gt=0,
        price_per_kg__gt=0,
    ).exclude(sale__status__in=['Gagal', 'Expired', 'Dibatalkan', 'Refund'])
    if cycle is not None:
        valid_items = valid_items.filter(sale__cycle=cycle)

    latest_item = valid_items.order_by('-sale__date', '-sale_id', '-id').first()
    if latest_item is not None:
        latest_sale = latest_item.sale
        latest_items = valid_items.filter(sale=latest_sale)
        totals = latest_items.aggregate(weight=Sum('weight_kg'), amount=Sum('subtotal'))
        weight = _decimal(totals.get('weight'))
        amount = _decimal(totals.get('amount'))
        if weight > 0 and amount > 0:
            return {
                'price': (amount / weight).quantize(Decimal('0.01')),
                'source': 'Harga jual transaksi panen terbaru',
                'date': timezone.localtime(latest_sale.date).date() if timezone.is_aware(latest_sale.date) else latest_sale.date.date(),
                'invoice_no': latest_sale.invoice_no,
                'sale_id': latest_sale.pk,
            }

    # Fallback untuk instalasi lama yang belum memiliki SaleItem lengkap.
    sales = Sale.objects.filter(
        date__date__lte=as_of, total_kg__gt=0, total_amount__gt=0
    ).exclude(status__in=['Gagal', 'Expired', 'Dibatalkan', 'Refund'])
    if cycle is not None:
        sales = sales.filter(cycle=cycle)
    latest_sale = sales.order_by('-date', '-id').first()
    if latest_sale is not None and _decimal(latest_sale.total_kg) > 0:
        return {
            'price': (_decimal(latest_sale.total_amount) / _decimal(latest_sale.total_kg)).quantize(Decimal('0.01')),
            'source': 'Harga nota penjualan terbaru',
            'date': timezone.localtime(latest_sale.date).date() if timezone.is_aware(latest_sale.date) else latest_sale.date.date(),
            'invoice_no': latest_sale.invoice_no,
            'sale_id': latest_sale.pk,
        }

    average_price, average_source = weighted_average_sale_price(cycle=cycle, as_of=as_of)
    return {
        'price': average_price,
        'source': average_source,
        'date': None,
        'invoice_no': '',
        'sale_id': None,
    }

def outstanding_payables(*, cycle=None, as_of=None):
    """Saldo utang yang belum dibayar sampai tanggal laporan."""
    as_of = as_of or timezone.localdate()
    qs = TradeAccount.objects.filter(
        account_type=TradeAccount.PAYABLE,
        transaction_date__lte=as_of,
    ).prefetch_related('payments')
    if cycle is not None:
        qs = qs.filter(cycle=cycle)

    total = ZERO
    count = 0
    for account in qs:
        paid = account.payments.filter(payment_date__lte=as_of).aggregate(total=Sum('amount'))['total'] or ZERO
        balance = max(_decimal(account.original_amount) - _decimal(paid), ZERO)
        if balance > 0:
            total += balance
            count += 1
    return total.quantize(Decimal('0.01')), count


def calculate_final_cycle_profit(*, cycle=None, as_of=None, simulated_price=None,
                                 tax_rate=TAX_RATE_DEFAULT, owner_share=Decimal('0.30'),
                                 retained_share=Decimal('0.40'), manager_share=Decimal('0.30')):
    """Proyeksi laba bersih jika biomassa Index dipanen dan utang dilunasi.

    Aplikasi saat ini memakai basis kas untuk pembayaran utang, sehingga saldo
    utang belum dibayar ditambahkan ke estimasi biaya akhir. Nilai sisa udang
    menggunakan Biomassa Index dan harga jual rata-rata tertimbang aktual.
    """
    as_of = as_of or timezone.localdate()
    if cycle is None:
        cycle = CultivationCycle.objects.filter(status=CultivationCycle.STATUS_ACTIVE).order_by('-start_date', '-id').first()

    finance = calculate_profit_loss(cycle=cycle, date_to=as_of)
    realized_revenue = _decimal(finance.get('revenue'))
    current_expenses = _decimal(finance.get('expense_total'))
    operating_profit = _decimal(finance.get('profit'))

    # Snapshot harus dihitung langsung untuk siklus terpilih. Sebelumnya
    # snapshot mengambil sampling terbaru per kolam tanpa filter siklus, lalu
    # hasilnya baru difilter di sini. Jika sampling terbaru berasal dari siklus
    # lain, hasil akhir menjadi 0 walaupun siklus terpilih mempunyai biomassa.
    snapshot = calculate_index_biomass_snapshot(as_of=as_of, cycle=cycle)
    rows = snapshot.get('rows', [])
    remaining_biomass_kg = sum((_decimal(row.biomass_index_kg) for row in rows), ZERO)

    latest_price_info = latest_harvest_sale_price(cycle=cycle, as_of=as_of)
    latest_price = _decimal(latest_price_info.get('price'))
    simulation_price = _decimal(simulated_price)
    price_used = simulation_price if simulation_price > 0 else latest_price
    price_source = latest_price_info.get('source') or 'Harga belum tersedia'
    if simulation_price > 0:
        price_source = 'Harga simulasi pengguna'

    remaining_biomass_value = (remaining_biomass_kg * price_used).quantize(Decimal('0.01'))
    projected_revenue = realized_revenue + remaining_biomass_value

    unpaid_payables, unpaid_count = outstanding_payables(cycle=cycle, as_of=as_of)
    projected_expenses = current_expenses + unpaid_payables
    tax_rate = _decimal(tax_rate)
    estimated_tax = (projected_revenue * tax_rate).quantize(Decimal('0.01'))
    final_profit_before_tax = projected_revenue - projected_expenses
    final_net_profit = final_profit_before_tax - estimated_tax
    margin = (final_net_profit / projected_revenue * Decimal('100')) if projected_revenue > 0 else ZERO

    owner_amount = (final_net_profit * _decimal(owner_share)).quantize(Decimal('0.01'))
    retained_amount = (final_net_profit * _decimal(retained_share)).quantize(Decimal('0.01'))
    manager_amount = final_net_profit - owner_amount - retained_amount

    return {
        'cycle': cycle,
        'as_of': as_of,
        'operating_profit': operating_profit,
        'realized_revenue': realized_revenue,
        'current_expenses': current_expenses,
        'remaining_biomass_kg': remaining_biomass_kg.quantize(Decimal('0.01')),
        'biomass_pond_count': len(rows),
        'biomass_excluded_pond_count': len(snapshot.get('excluded', [])),
        'average_sale_price': latest_price,  # kompatibilitas template lama
        'latest_harvest_price': latest_price,
        'latest_harvest_price_date': latest_price_info.get('date'),
        'latest_harvest_invoice_no': latest_price_info.get('invoice_no', ''),
        'price_used': price_used.quantize(Decimal('0.01')),
        'price_source': price_source,
        'remaining_biomass_value': remaining_biomass_value,
        'projected_revenue': projected_revenue.quantize(Decimal('0.01')),
        'unpaid_payables': unpaid_payables,
        'unpaid_payables_count': unpaid_count,
        'projected_expenses': projected_expenses.quantize(Decimal('0.01')),
        'tax_rate': tax_rate,
        'estimated_tax': estimated_tax,
        'final_profit_before_tax': final_profit_before_tax.quantize(Decimal('0.01')),
        'final_net_profit': final_net_profit.quantize(Decimal('0.01')),
        'final_margin_percent': margin.quantize(Decimal('0.01')),
        'owner_share_percent': _decimal(owner_share) * Decimal('100'),
        'retained_share_percent': _decimal(retained_share) * Decimal('100'),
        'manager_share_percent': _decimal(manager_share) * Decimal('100'),
        'owner_amount': owner_amount,
        'retained_amount': retained_amount,
        'manager_amount': manager_amount.quantize(Decimal('0.01')),
        'is_profitable': final_net_profit > 0,
        'has_price': price_used > 0,
    }
