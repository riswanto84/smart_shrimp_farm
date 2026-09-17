from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory

from finance.models import BiologicalAssetValuation
from finance.views import _balance_sheet_data


class Command(BaseCommand):
    help = (
        'Menyimpan snapshot/baseline nilai aset biologis berdasarkan perhitungan '
        'Neraca. Jalankan sekali setelah deployment, lalu dapat dijalankan kembali '
        'pada tanggal penutupan periode.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--date', dest='valuation_date', default=None,
            help='Tanggal penilaian YYYY-MM-DD. Default: hari ini.',
        )
        parser.add_argument(
            '--replace', action='store_true',
            help='Perbarui snapshot jika tanggal tersebut sudah ada.',
        )

    def handle(self, *args, **options):
        raw_date = options.get('valuation_date')
        try:
            valuation_date = date.fromisoformat(raw_date) if raw_date else date.today()
        except ValueError as exc:
            raise CommandError('Format --date harus YYYY-MM-DD.') from exc

        request = RequestFactory().get('/finance/tax/balance/', {'as_of': valuation_date.isoformat()})
        data = _balance_sheet_data(request)
        value = data['biological_assets_total']

        existing = BiologicalAssetValuation.objects.filter(valuation_date=valuation_date).first()
        if existing and not options.get('replace'):
            raise CommandError(
                f'Snapshot {valuation_date} sudah ada sebesar {existing.closing_value}. '
                'Gunakan --replace untuk memperbarui.'
            )

        obj, created = BiologicalAssetValuation.objects.update_or_create(
            valuation_date=valuation_date,
            defaults={
                'closing_value': value,
                'notes': 'Snapshot otomatis dari perhitungan Neraca Smart Shrimp Farm.',
            },
        )
        action = 'dibuat' if created else 'diperbarui'
        self.stdout.write(self.style.SUCCESS(
            f'Snapshot aset biologis {valuation_date} berhasil {action}: Rp {value:,.2f}'
        ))
