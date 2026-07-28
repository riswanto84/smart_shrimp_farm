from django.core.management.base import BaseCommand
from django.db import transaction

from sales.models import Sale
from finance.receivable_sync import sync_sale_receivable


class Command(BaseCommand):
    help = "Segarkan kartu piutang berdasarkan status yang tersimpan pada nota."

    @transaction.atomic
    def handle(self, *args, **options):
        checked = 0
        synced = 0

        for sale in Sale.objects.all().order_by("pk").iterator():
            checked += 1
            if sync_sale_receivable(sale) is not None:
                synced += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai. {checked} nota diperiksa dan "
                f"{synced} kartu piutang disegarkan."
            )
        )
