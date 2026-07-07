from datetime import date, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from ponds.models import Pond
from operations.models import Stocking, DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord, Harvest
from sales.models import Customer, Sale, SaleItem


class Command(BaseCommand):
    help = (
        'Tambah data operasional demo: cek anco harian, sampling, siphon, panen, dan nota penjualan. '
        'Contoh: python manage.py seed_operational_data --count 50 --reset'
    )

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=50, help='Jumlah data untuk masing-masing modul')
        parser.add_argument('--reset', action='store_true', help='Hapus data demo operasional/penjualan lama sebelum seed')

    def handle(self, *args, **opts):
        count = max(1, int(opts.get('count') or 50))
        reset = bool(opts.get('reset'))
        random.seed(84)

        ponds = list(Pond.objects.all().order_by('code'))
        if not ponds:
            self.stdout.write(self.style.ERROR('Belum ada data kolam. Jalankan python manage.py seed_demo --count 50 --reset terlebih dahulu.'))
            return

        admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
        base_date = date.today()

        if reset:
            SaleItem.objects.all().delete()
            Sale.objects.all().delete()
            AncoCheck.objects.all().delete()
            SamplingRecord.objects.all().delete()
            SiphonRecord.objects.all().delete()
            Harvest.objects.all().delete()

        customers = self._seed_customers()
        self._ensure_stocking_and_daily_feed(ponds, admin, base_date)
        self._seed_anco_checks(ponds, admin, base_date, count)
        self._seed_sampling_records(ponds, base_date, count)
        self._seed_siphon_records(ponds, admin, base_date, count)
        harvests = self._seed_harvests(ponds, base_date, count)
        self._seed_sales(customers, harvests, admin, count)

        self.stdout.write(self.style.SUCCESS(
            f'Berhasil membuat {count} data cek anco harian, {count} data sampling, '
            f'{count} data siphon, {count} data panen, dan {count} nota penjualan.'
        ))

    def _seed_customers(self):
        data = [
            ('PT Bahari Sentosa', '0812-1111-2222', 'purchasing@bahari.co.id', 'Jakarta'),
            ('UD Samudra Jaya', '0813-3333-4444', 'samudra@example.com', 'Bekasi'),
            ('CV Mina Laut Mandiri', '0812-5555-7777', 'minalaut@example.com', 'Karawang'),
            ('Resto Bahari Seafood', '0818-2222-3333', 'resto@example.com', 'Bekasi'),
            ('PT Bintang Sejahtera', '0819-8888-9999', 'bintang@example.com', 'Tangerang'),
            ('Pasar Ikan Modern Bekasi', '0821-7777-1111', 'pim@example.com', 'Bekasi'),
            ('Dapur Seafood Nusantara', '0822-3333-9999', 'dapur@example.com', 'Jakarta'),
            ('Distributor Udang Fresh', '0823-5555-1111', 'fresh@example.com', 'Cikarang'),
        ]
        customers = []
        for name, phone, email, address in data:
            c, _ = Customer.objects.update_or_create(
                name=name,
                defaults={'phone': phone, 'email': email, 'address': address},
            )
            customers.append(c)
        return customers

    def _ensure_stocking_and_daily_feed(self, ponds, admin, base_date):
        for idx, pond in enumerate(ponds[:5], start=1):
            Stocking.objects.get_or_create(
                pond=pond,
                date=base_date - timedelta(days=65 + idx),
                defaults={
                    'seed_count': 180000 + idx * 5000,
                    'hatchery': 'Hatchery Nusantara',
                    'notes': 'Seed otomatis operasional',
                },
            )
            for d in range(70):
                tgl = base_date - timedelta(days=d)
                DailyPondRecord.objects.update_or_create(
                    pond=pond,
                    date=tgl,
                    defaults={
                        'technician': admin,
                        'doc': max(1, 70 - d),
                        'feed_code': f'781-{1 + d % 3}',
                        'daily_feed_kg': Decimal('25.00') + Decimal((idx + d) % 25),
                        'water_in_cm': Decimal('3.00') + Decimal(d % 4),
                        'weather': random.choice(['Cerah', 'Berawan', 'Panas', 'Hujan']),
                        'treatment': 'Probiotik' if d % 7 == 0 else '',
                        'notes': 'Data pendukung seed sampling dan anco',
                    },
                )

    def _seed_anco_checks(self, ponds, admin, base_date, count):
        patterns = [
            ('H', 'H', 'H', 'H', 'H', 'H', 'Nafsu makan kuat, pakan dapat dipertahankan.'),
            ('H', 'H', 'S', 'H', 'H', 'S', 'Ada sisa ringan, evaluasi pakan siang/sore.'),
            ('S', 'S', 'H', 'S', 'H', 'S', 'Nafsu makan menurun, pertahankan atau turunkan pakan 5–10%.'),
            ('SS', 'S', 'H', 'SS', 'S', 'H', 'Sisa banyak, cek DO, pH, suhu, dan kondisi dasar kolam.'),
            ('H', 'S', 'H', 'S', 'H', 'H', 'Respons masih baik, pantau tren besok.'),
        ]
        for i in range(count):
            pond = ponds[i % len(ponds)]
            tanggal = base_date - timedelta(days=i)
            p = patterns[i % len(patterns)]
            AncoCheck.objects.update_or_create(
                pond=pond,
                date=tanggal,
                defaults={
                    'technician': admin,
                    'doc': 29 + (i % 45),
                    'anco1_morning': p[0],
                    'anco2_morning': p[1],
                    'anco1_noon': p[2],
                    'anco2_noon': p[3],
                    'anco1_evening': p[4],
                    'anco2_evening': p[5],
                    'notes': f'Data cek anco dummy #{i + 1}. {p[6]}',
                },
            )

    def _seed_sampling_records(self, ponds, base_date, count):
        made = 0
        week = 0
        while made < count:
            for pond in ponds[:5]:
                if made >= count:
                    break
                tanggal = base_date - timedelta(days=week * 7)
                doc = max(7, 29 + week * 7 + (made % 5))
                abw = Decimal('2.50') + Decimal(week) * Decimal('1.05') + Decimal(made % 5) / Decimal('10')
                sample_count = 80 + (made % 25)
                sample_weight = (abw * Decimal(sample_count)).quantize(Decimal('0.01'))
                stocking = Stocking.objects.filter(pond=pond, date__lte=tanggal).order_by('-date').first()
                tebar = stocking.seed_count if stocking else 180000
                SamplingRecord.objects.update_or_create(
                    pond=pond,
                    date=tanggal,
                    defaults={
                        'doc': doc,
                        'sample_weight_g': sample_weight,
                        'sample_count': sample_count,
                        'adg_weekly_target': Decimal('0.20'),
                        'cumulative_feed_kg': Decimal('380.00') + Decimal(made * 9),
                        'stocking_count': tebar,
                        'daily_feed_kg': Decimal('28.00') + Decimal(made % 20),
                        'fr_percent': Decimal('6.00') + Decimal(made % 8) / Decimal('10'),
                        'population_index': int(Decimal(tebar) * (Decimal('0.80') - Decimal(made % 8) / Decimal('100'))),
                        'index_score': Decimal('0.500'),
                        'notes': 'Data sampling dummy otomatis sebanyak 50 data',
                    },
                )
                made += 1
            week += 1

    def _seed_siphon_records(self, ponds, admin, base_date, count):
        for i in range(count):
            pond = ponds[i % len(ponds)]
            tanggal = base_date - timedelta(days=i)
            SiphonRecord.objects.update_or_create(
                pond=pond,
                date=tanggal,
                defaults={
                    'technician': admin,
                    'doc': 29 + (i % 45),
                    'dead_count': (i * 4) % 110,
                    'live_count': i % 10,
                    'notes': 'Data siphon dummy otomatis sebanyak 50 data',
                },
            )

    def _seed_harvests(self, ponds, base_date, count):
        harvests = []
        for i in range(count):
            pond = ponds[i % min(len(ponds), 5)]
            tanggal = base_date - timedelta(days=i * 2)
            harvest_type = 'Parsial' if i % 4 else 'Total'
            h, _ = Harvest.objects.update_or_create(
                pond=pond,
                date=tanggal,
                harvest_type=harvest_type,
                defaults={
                    'size_text': str(random.choice([40, 50, 60, 70, 80])),
                    'total_kg': Decimal('350.00') + Decimal(i * 35),
                    'notes': 'Data panen dummy otomatis sebanyak 50 data',
                },
            )
            harvests.append(h)
        return harvests

    def _seed_sales(self, customers, harvests, admin, count):
        if not customers or not harvests:
            return
        methods = ['Cash', 'Transfer', 'QRIS', 'Midtrans']
        statuses = ['Lunas', 'Lunas', 'Belum Lunas', 'Menunggu Pembayaran']
        for i in range(count):
            customer = customers[i % len(customers)]
            harvest = harvests[i % len(harvests)]
            kg = Decimal('25.00') + Decimal(i % 18) * Decimal('5.00')
            price = Decimal(random.choice([65000, 68000, 70000, 72000]))
            subtotal = kg * price
            shipping = Decimal('15000') if i % 2 == 0 else Decimal('0')
            packing = Decimal('10000') if i % 3 == 0 else Decimal('0')
            other = Decimal('5000') if i % 5 == 0 else Decimal('0')
            invoice = f'INV/DEMO/2026/07/{i + 1:04d}'
            sale, _ = Sale.objects.update_or_create(
                invoice_no=invoice,
                defaults={
                    'customer': customer,
                    'total_kg': kg,
                    'total_amount': subtotal + shipping + packing + other,
                    'shipping_cost': shipping,
                    'packing_cost': packing,
                    'other_cost': other,
                    'payment_method': methods[i % len(methods)],
                    'status': statuses[i % len(statuses)],
                    'cashier': admin,
                    'notes': 'Data dummy nota penjualan otomatis sebanyak 50 data',
                },
            )
            sale.items.all().delete()
            SaleItem.objects.create(
                sale=sale,
                harvest=harvest,
                size_text=harvest.size_text,
                weight_kg=kg,
                price_per_kg=price,
                subtotal=subtotal,
            )
