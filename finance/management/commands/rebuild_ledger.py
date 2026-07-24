from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from finance.ledger import rebuild_system_ledger


class Command(BaseCommand):
    help = 'Bangun ulang jurnal sistem dari transaksi aplikasi.'

    def add_arguments(self, parser):
        parser.add_argument('--as-of', dest='as_of', help='Tanggal YYYY-MM-DD')

    def handle(self, *args, **options):
        as_of = parse_date(options.get('as_of') or '') if options.get('as_of') else None
        result = rebuild_system_ledger(as_of)
        self.stdout.write(self.style.SUCCESS(
            f"Ledger selesai: {result['entries']} jurnal, {result['lines']} baris. "
            f"Selisih saldo awal: {result['opening_difference']}"
        ))
