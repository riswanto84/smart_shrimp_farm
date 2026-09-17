from django.core.management.base import BaseCommand

from finance.receivable_sync import sync_all_sales


class Command(BaseCommand):
    help = 'Sinkronkan seluruh Nota Penjualan dengan kartu Piutang Usaha.'

    def handle(self, *args, **options):
        count = sync_all_sales()
        self.stdout.write(self.style.SUCCESS(
            f'Sinkronisasi selesai. {count} kartu piutang otomatis aktif/diperbarui.'
        ))
