from datetime import date, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from accounts.models import Role, PermissionItem, AuditLog
from ponds.models import Pond
from operations.models import (
    Stocking,
    DailyParameter,
    Harvest,
    Treatment,
    FeedLog,
    DailyPondRecord,
    AncoCheck,
    SamplingRecord,
    SiphonRecord,
)
from sales.models import Customer, Sale, SaleItem
from finance.models import OperationalExpense


class Command(BaseCommand):
    help = 'Isi data dummy SMART SHRIMP FARM termasuk 50 sampling, 50 siphon, dan 50 panen jika --count 50.'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=20, help='Jumlah data dummy per modul utama, contoh: --count 50')
        parser.add_argument('--reset', action='store_true', help='Hapus data demo lama sebelum membuat data baru')

    def handle(self, *args, **opts):
        count = max(1, int(opts.get('count') or 20))
        reset = bool(opts.get('reset'))
        random.seed(21)

        if reset:
            self._reset_demo_data()

        admin = self._seed_roles_users()
        ponds = self._seed_ponds()
        customers = self._seed_customers()
        base_date = date(2026, 7, 7)

        self._seed_stocking(ponds, base_date)
        self._seed_daily_parameters(ponds, admin, base_date, count)
        self._seed_daily_pond_records(ponds, admin, base_date, count)
        self._seed_anco_checks(ponds, admin, base_date, count)
        self._seed_sampling_records(ponds, base_date, count)
        self._seed_siphon_records(ponds, admin, base_date, count)
        harvests = self._seed_harvests(ponds, base_date, count)
        self._seed_sales(customers, harvests, admin, base_date, count)
        self._seed_expenses(ponds, base_date, count)

        AuditLog.objects.get_or_create(user=admin, action=f'Data dummy SMART SHRIMP FARM dibuat sebanyak {count} data')
        self.stdout.write(self.style.SUCCESS(f'Data dummy berhasil dibuat: {count} data per modul utama. Login: riswanto / admin12345'))

    def _reset_demo_data(self):
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        Customer.objects.all().delete()
        OperationalExpense.objects.all().delete()
        SiphonRecord.objects.all().delete()
        SamplingRecord.objects.all().delete()
        AncoCheck.objects.all().delete()
        DailyPondRecord.objects.all().delete()
        DailyParameter.objects.all().delete()
        FeedLog.objects.all().delete()
        Treatment.objects.all().delete()
        Harvest.objects.all().delete()
        Stocking.objects.all().delete()
        AuditLog.objects.all().delete()

    def _seed_roles_users(self):
        roles = [
            ('Owner', 'Akses penuh owner'),
            ('Admin', 'Kelola data operasional dan laporan'),
            ('Teknisi', 'Input parameter, pakan, treatment'),
            ('Kasir', 'Input penjualan dan nota'),
            ('Investor', 'Lihat dashboard investor read only'),
            ('Akuntan', 'Kelola keuangan'),
        ]
        role_objs = {}
        for name, desc in roles:
            role_objs[name], _ = Role.objects.get_or_create(name=name, defaults={'description': desc})

        perms = [
            'dashboard.view', 'kolam.view', 'kolam.add', 'kolam.edit', 'parameter.view', 'parameter.add',
            'panen.view', 'panen.add', 'sales.view', 'sales.add', 'finance.view', 'finance.add',
            'finance.periodic_report', 'investor.view', 'laporan.export', 'users.manage',
            'operations.view', 'operations.add', 'operations.edit', 'operations.delete',
        ]
        for code in perms:
            PermissionItem.objects.get_or_create(code=code, defaults={'name': code.replace('.', ' ').title(), 'group': code.split('.')[0]})

        admin, created = User.objects.get_or_create(username='riswanto', defaults={'email': 'riswanto@udangemasnusantara.com', 'first_name': 'Riswanto'})
        if created:
            admin.set_password('admin12345')
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
        elif not admin.is_superuser:
            admin.is_staff = True
            admin.is_superuser = True
            admin.save(update_fields=['is_staff', 'is_superuser'])
        admin.userprofile.roles.set([role_objs['Owner'], role_objs['Admin']])

        demo_users = [
            ('budi', ['Teknisi', 'Kasir']),
            ('ahmad', ['Teknisi']),
            ('investor.a', ['Investor']),
            ('akuntan', ['Akuntan']),
        ]
        for uname, roleset in demo_users:
            u, created = User.objects.get_or_create(username=uname, defaults={'email': uname + '@example.com', 'first_name': uname.title()})
            if created:
                u.set_password('12345678')
                u.save()
            u.userprofile.roles.set([role_objs[r] for r in roleset])
        return admin

    def _seed_ponds(self):
        data = [
            ('K-01', 'Kolam 1', 1848, 'Budidaya'),
            ('K-02', 'Kolam 2', 1848, 'Budidaya'),
            ('K-03', 'Kolam 3', 1848, 'Budidaya'),
            ('K-04', 'Kolam 4', 1848, 'Budidaya'),
            ('K-05', 'Kolam 5', 1848, 'Panen'),
            ('K-06', 'Kolam 6', 1707, 'Persiapan'),
        ]
        ponds = []
        for code, name, area, status in data:
            pond, _ = Pond.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'area_m2': area,
                    'depth_m': Decimal('1.40'),
                    'capacity_seed': 200000 if status in ['Budidaya', 'Panen'] else 0,
                    'pond_type': 'HDPE',
                    'status': status,
                    'location': 'Jalan Pantai Mekar, Muara Gembong, Kabupaten Bekasi',
                    'notes': 'Data dummy aplikasi Smart Shrimp Farm',
                },
            )
            ponds.append(pond)
        return ponds

    def _seed_customers(self):
        names = [
            ('PT Bahari Sentosa', '0812-1111-2222', 'purchasing@bahari.co.id', 'Jakarta'),
            ('UD Samudra Jaya', '0813-3333-4444', 'samudra@example.com', 'Bekasi'),
            ('CV Mina Laut Mandiri', '0812-5555-7777', 'minalaut@example.com', 'Karawang'),
            ('Resto Bahari Seafood', '0818-2222-3333', 'resto@example.com', 'Bekasi'),
            ('PT Bintang Sejahtera', '0819-8888-9999', 'bintang@example.com', 'Tangerang'),
        ]
        customers = []
        for name, phone, email, address in names:
            c, _ = Customer.objects.get_or_create(name=name, defaults={'phone': phone, 'email': email, 'address': address})
            customers.append(c)
        return customers

    def _seed_stocking(self, ponds, base_date):
        for idx, pond in enumerate(ponds[:5], start=1):
            Stocking.objects.update_or_create(
                pond=pond,
                date=base_date - timedelta(days=55 + idx),
                defaults={'seed_count': 180000 + (idx * 5000), 'hatchery': 'Hatchery Nusantara', 'notes': 'Data tebar dummy'},
            )

    def _seed_daily_parameters(self, ponds, admin, base_date, count):
        for i in range(count):
            pond = ponds[i % len(ponds)]
            tanggal = base_date - timedelta(days=i)
            DailyParameter.objects.update_or_create(
                pond=pond,
                date=tanggal,
                defaults={
                    'technician': admin,
                    'doc': 29 + (i % 40),
                    'water_level_cm': Decimal('75.00') + Decimal(i % 36),
                    'temperature': Decimal('28.00') + Decimal(i % 12) / Decimal('10'),
                    'ph_morning': Decimal('7.40') + Decimal(i % 5) / Decimal('10'),
                    'ph_evening': Decimal('7.70') + Decimal(i % 4) / Decimal('10'),
                    'do_morning': Decimal('5.20') + Decimal(i % 5) / Decimal('10'),
                    'do_night': Decimal('4.90') + Decimal(i % 4) / Decimal('10'),
                    'salinity': Decimal('18.00') + Decimal(i % 3),
                    'alkalinity': Decimal('120.00') + Decimal(i % 8),
                    'transparency': Decimal('35.00') + Decimal(i % 5),
                    'feed_kg': Decimal('30.00') + Decimal(i % 20),
                    'mortality': i % 18,
                    'water_color': random.choice(['Hijau kecoklatan', 'Coklat muda', 'Hijau plankton', 'Cerah kehijauan']),
                    'ai_recommendation': 'Kondisi relatif stabil. Pantau DO pagi dan respons pakan melalui anco.',
                },
            )
            FeedLog.objects.update_or_create(pond=pond, date=tanggal, defaults={'feed_name': f'Pelet 781-{1 + (i % 3)}', 'quantity_kg': Decimal('30.00') + Decimal(i % 20)})
            if i % 7 == 0:
                Treatment.objects.update_or_create(pond=pond, date=tanggal, name='Probiotik', defaults={'dose': '0,2 ppm', 'notes': 'Treatment dummy rutin'})

    def _seed_daily_pond_records(self, ponds, admin, base_date, count):
        for i in range(count):
            pond = ponds[i % len(ponds)]
            tanggal = base_date - timedelta(days=i)
            DailyPondRecord.objects.update_or_create(
                pond=pond,
                date=tanggal,
                defaults={
                    'technician': admin,
                    'doc': 29 + (i % 40),
                    'feed_code': f'781-{1 + (i % 3)}',
                    'daily_feed_kg': Decimal('28.00') + Decimal(i % 22),
                    'water_in_cm': Decimal('4.00') + Decimal(i % 4),
                    'weather': random.choice(['Cerah', 'Berawan', 'Hujan', 'Panas']),
                    'treatment': 'Probiotik dan mineral sesuai kebutuhan' if i % 3 == 0 else '',
                    'notes': 'Data harian dummy',
                },
            )

    def _seed_anco_checks(self, ponds, admin, base_date, count):
        patterns = [
            ('H', 'H', 'H', 'H', 'H', 'H'),
            ('H', 'H', 'S', 'H', 'H', 'S'),
            ('S', 'S', 'H', 'S', 'H', 'S'),
            ('SS', 'S', 'H', 'SS', 'S', 'H'),
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
                    'doc': 29 + (i % 40),
                    'anco1_morning': p[0], 'anco2_morning': p[1],
                    'anco1_noon': p[2], 'anco2_noon': p[3],
                    'anco1_evening': p[4], 'anco2_evening': p[5],
                    'notes': 'Cek anco dummy',
                },
            )

    def _seed_sampling_records(self, ponds, base_date, count):
        # Sampling dibuat per 7 hari agar ADG weekly otomatis terbaca dari sampling sebelumnya.
        loops = max(count, len(ponds) * 3)
        made = 0
        week = 0
        while made < count:
            for pond in ponds[:5]:
                if made >= count:
                    break
                tanggal = base_date - timedelta(days=week * 7)
                doc = 29 + (week * 7) + (made % 5)
                abw_target = Decimal('2.60') + Decimal(week) * Decimal('1.10') + Decimal(made % 5) / Decimal('10')
                sample_count = 80 + (made % 25)
                sample_weight = (abw_target * Decimal(sample_count)).quantize(Decimal('0.01'))
                fr = Decimal('6.00') + Decimal(made % 6) / Decimal('10')
                daily_feed = Decimal('30.00') + Decimal(made % 18)
                stocking = 180000 + ((made % 5) * 5000)
                SamplingRecord.objects.update_or_create(
                    pond=pond,
                    date=tanggal,
                    defaults={
                        'doc': doc,
                        'sample_weight_g': sample_weight,
                        'sample_count': sample_count,
                        'adg_weekly_target': Decimal('0.20'),
                        'cumulative_feed_kg': Decimal('400.00') + Decimal(made * 8),
                        'stocking_count': stocking,
                        'daily_feed_kg': daily_feed,
                        'fr_percent': fr,
                        'population_index': int(stocking * Decimal('0.78')),
                        'index_score': Decimal('0.500'),
                        'notes': 'Sampling dummy sesuai struktur Excel',
                    },
                )
                made += 1
            week += 1
            if week > loops:
                break

    def _seed_siphon_records(self, ponds, admin, base_date, count):
        for i in range(count):
            pond = ponds[i % len(ponds)]
            tanggal = base_date - timedelta(days=i)
            SiphonRecord.objects.update_or_create(
                pond=pond,
                date=tanggal,
                defaults={
                    'technician': admin,
                    'doc': 29 + (i % 40),
                    'dead_count': (i * 3) % 90,
                    'live_count': i % 8,
                    'notes': 'Data siphon dummy',
                },
            )

    def _seed_harvests(self, ponds, base_date, count):
        harvests = []
        for i in range(count):
            pond = ponds[i % 5]
            tanggal = base_date - timedelta(days=i * 3)
            h, _ = Harvest.objects.update_or_create(
                pond=pond,
                date=tanggal,
                harvest_type='Parsial' if i % 3 else 'Total',
                defaults={'size_text': str(random.choice([40, 50, 60, 70])), 'total_kg': Decimal('600.00') + Decimal(i * 125), 'notes': 'Panen dummy'},
            )
            harvests.append(h)
        return harvests

    def _seed_sales(self, customers, harvests, admin, base_date, count):
        methods = ['Cash', 'Transfer', 'Midtrans', 'QRIS']
        statuses = ['Lunas', 'Belum Lunas', 'Menunggu Pembayaran']
        for i in range(count):
            customer = customers[i % len(customers)]
            harvest = harvests[i % len(harvests)]
            kg = Decimal('25.00') + Decimal(i % 18) * Decimal('5.00')
            price = Decimal(random.choice([65000, 68000, 70000, 72000]))
            subtotal = kg * price
            invoice = f'INV/2026/07/{i + 1:04d}'
            sale, _ = Sale.objects.update_or_create(
                invoice_no=invoice,
                defaults={
                    'customer': customer,
                    'total_kg': kg,
                    'total_amount': subtotal + Decimal('15000') + Decimal((i % 3) * 10000),
                    'shipping_cost': Decimal('15000') if i % 2 == 0 else Decimal('0'),
                    'packing_cost': Decimal('10000') if i % 3 == 0 else Decimal('0'),
                    'other_cost': Decimal('5000') if i % 5 == 0 else Decimal('0'),
                    'payment_method': methods[i % len(methods)],
                    'status': statuses[i % len(statuses)],
                    'cashier': admin,
                    'notes': 'Data dummy penjualan',
                },
            )
            sale.items.all().delete()
            SaleItem.objects.create(sale=sale, harvest=harvest, size_text=harvest.size_text, weight_kg=kg, price_per_kg=price, subtotal=subtotal)

    def _seed_expenses(self, ponds, base_date, count):
        categories = ['Pakan', 'Listrik', 'BBM', 'Obat & Probiotik', 'Tenaga Kerja', 'Peralatan', 'Transportasi', 'Lain-lain']
        for i in range(count):
            tanggal = base_date - timedelta(days=i)
            cat = categories[i % len(categories)]
            pond = ponds[i % len(ponds)] if i % 2 == 0 else None
            OperationalExpense.objects.update_or_create(
                date=tanggal,
                category=cat,
                name=f'{cat} #{i + 1}',
                defaults={
                    'amount': Decimal(250000 + (i % 15) * 175000),
                    'pond': pond,
                    'payment_method': 'Transfer' if i % 2 == 0 else 'Cash',
                    'notes': 'Data dummy pengeluaran operasional',
                },
            )
