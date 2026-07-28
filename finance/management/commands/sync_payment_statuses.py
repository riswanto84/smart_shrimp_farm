from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from sales.models import Sale

try:
    from finance.services import sync_sale_receivable
except ImportError:
    try:
        from finance.utils import sync_sale_receivable
    except ImportError:
        from sales.views import sync_sale_receivable


class Command(BaseCommand):
    help = (
        "Sinkronkan status seluruh Nota Penjualan dengan saldo Piutang Usaha. "
        "Saldo 0 menjadi Lunas, saldo di atas 0 menjadi Belum Lunas."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        updated = 0
        checked = 0

        queryset = Sale.objects.all().order_by("pk")
        for sale in queryset.iterator():
            checked += 1
            old_status = sale.status
            sync_sale_receivable(sale)
            sale.refresh_from_db(fields=["status"])

            if sale.status != old_status:
                updated += 1
                self.stdout.write(
                    f"{sale.invoice_no}: {old_status} -> {sale.status}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai. {checked} nota diperiksa, {updated} status diperbarui."
            )
        )
