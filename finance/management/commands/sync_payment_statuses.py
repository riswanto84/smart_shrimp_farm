from django.core.management.base import BaseCommand
from django.db import transaction

from sales.models import Sale
from finance.receivable_sync import sync_sale_receivable


class Command(BaseCommand):
    help = "Sinkronkan status Nota Penjualan berdasarkan pembayaran aktual."

    @transaction.atomic
    def handle(self, *args, **options):
        checked = 0
        updated = 0

        for sale in Sale.objects.all().order_by("pk").iterator():
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
