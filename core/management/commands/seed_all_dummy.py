from datetime import date, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import Role, PermissionItem, AuditLog
from ponds.models import Pond
from operations.models import (
    Stocking,
    DailyParameter,
    Treatment,
    FeedLog,
    Harvest,
    DailyPondRecord,
    AncoCheck,
    SamplingRecord,
    SiphonRecord,
)
from sales.models import Customer, Sale, SaleItem
from finance.models import OperationalExpense
from chat_ai.models import ChatSession, ChatMessage


class Command(BaseCommand):
    help = 'Membuat data dummy lengkap Smart Shrimp Farm. Default 50 data per modul transaksi.'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=50, help='Jumlah data per modul transaksi. Default: 50')
        parser.add_argument('--reset', action='store_true', help='Hapus data transaksi/master demo sebelum membuat data baru')

    def handle(self, *args, **options):
        count = max(1, int(options.get('count') or 50))
        reset = bool(options.get('reset'))
        random.seed(20260707)
        base_date = timezone.localdate()

        if reset:
            self._reset_data()

        users = self._seed_roles_permissions_users()
        admin = users['admin']
        ponds = self._seed_ponds()
        customers = self._seed_customers(count)

        self._seed_stocking(ponds, base_date)
        self._seed_daily_parameters(ponds, admin, base_date, count)
        self._seed_feed_logs(ponds, base_date, count)
        self._seed_treatments(ponds, base_date, count)
        self._seed_daily_pond_records(ponds, admin, base_date, count)
        self._seed_anco_checks(ponds, admin, base_date, count)
        self._seed_sampling_records(ponds, base_date, count)
        self._seed_siphon_records(ponds, admin, base_date, count)
        harvests = self._seed_harvests(ponds, base_date, count)
        self._seed_sales(customers, harvests, admin, base_date, count)
        self._seed_expenses(ponds, base_date, count)
        self._seed_chat_ai(users, ponds, count)

        AuditLog.objects.create(user=admin, action=f'Seed dummy lengkap Smart Shrimp Farm sebanyak {count} data per modul')
        self.stdout.write(self.style.SUCCESS('Data dummy lengkap berhasil dibuat.'))
        self.stdout.write(self.style.SUCCESS(f'- {len(ponds)} master kolam'))
        self.stdout.write(self.style.SUCCESS(f'- {count} data pelanggan, parameter, pakan, treatment, data harian, anco, sampling, siphon, panen, nota, pengeluaran'))
        self.stdout.write(self.style.SUCCESS('Login demo: riswanto / admin12345'))

    def _reset_data(self):
        ChatMessage.objects.all().delete()
        ChatSession.objects.all().delete()
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
        Pond.objects.all().delete()
        AuditLog.objects.all().delete()

    def _seed_roles_permissions_users(self):
        role_defs = [
            ('Owner', 'Akses penuh owner dan ringkasan investor'),
            ('Admin', 'Kelola data operasional dan laporan'),
            ('Teknisi', 'Input data kolam, anco, sampling, siphon'),
            ('Kasir', 'Input penjualan dan nota'),
            ('Investor', 'Lihat laporan dan ringkasan investor'),
            ('Akuntan', 'Kelola pengeluaran dan laporan keuangan'),
        ]
        roles = {}
        for name, desc in role_defs:
            roles[name], _ = Role.objects.get_or_create(name=name, defaults={'description': desc})

        perm_codes = [
            'dashboard.view', 'kolam.view', 'kolam.add', 'kolam.edit', 'kolam.delete',
            'operations.view', 'operations.add', 'operations.edit', 'operations.delete',
            'parameter.view', 'parameter.add', 'parameter.edit', 'parameter.delete',
            'panen.view', 'panen.add', 'panen.edit', 'panen.delete',
            'sales.view', 'sales.add', 'sales.edit', 'finance.view', 'finance.add', 'finance.edit', 'finance.delete',
            'finance.periodic_report', 'investor.view', 'laporan.export', 'users.manage',
            'ai.view', 'ai.generate', 'ollama.chat',
        ]
        for code in perm_codes:
            item, _ = PermissionItem.objects.get_or_create(
                code=code,
                defaults={'name': code.replace('.', ' ').title(), 'group': code.split('.')[0]},
            )
            # Admin dan owner mendapat semua permission.
            for role in (roles['Owner'], roles['Admin']):
                role.rolepermission_set.get_or_create(permission=item)

        admin, created = User.objects.get_or_create(
            username='riswanto',
            defaults={'email': 'riswanto@udangemasnusantara.com', 'first_name': 'Riswanto', 'last_name': 'Aris'},
        )
        admin.set_password('admin12345')
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        admin.userprofile.roles.set([roles['Owner'], roles['Admin']])

        demo = {
            'teknisi': ('Andi Teknisi', ['Teknisi']),
            'kasir': ('Rina Kasir', ['Kasir']),
            'akuntan': ('Dewi Akuntan', ['Akuntan']),
            'investor': ('Investor UEN', ['Investor']),
        }
        users = {'admin': admin}
        for username, (first_name, role_names) in demo.items():
            user, created = User.objects.get_or_create(username=username, defaults={'email': f'{username}@udangemasnusantara.com'})
            user.first_name = first_name
            user.set_password('12345678')
            user.save()
            user.userprofile.roles.set([roles[r] for r in role_names])
            users[username] = user
        return users

    def _seed_ponds(self):
        ponds = []
        for i in range(1, 13):
            status = 'Budidaya' if i <= 9 else ('Panen' if i <= 10 else 'Persiapan')
            pond, _ = Pond.objects.update_or_create(
                code=f'K-{i:02d}',
                defaults={
                    'name': f'Kolam {i}',
                    'area_m2': Decimal('1800.00') + Decimal(i * 25),
                    'depth_m': Decimal('1.35') + Decimal(i % 3) / Decimal('10'),
                    'capacity_seed': 175000 + (i * 2500),
                    'pond_type': 'HDPE' if i <= 10 else 'Tandon/Persiapan',
                    'status': status,
                    'location': 'Jalan Pantai Mekar, Kec. Muara Gembong, Kabupaten Bekasi, Jawa Barat 17730',
                    'notes': 'Data master kolam dummy untuk Smart Shrimp Farm',
                },
            )
            ponds.append(pond)
        return ponds

    def _seed_customers(self, count):
        prefixes = ['PT', 'CV', 'UD', 'Resto', 'Pasar Ikan', 'Distributor', 'Seafood', 'Cold Storage']
        names = ['Bahari Sentosa', 'Samudra Jaya', 'Mina Laut Mandiri', 'Bintang Sejahtera', 'Laut Makmur', 'Segar Abadi', 'Nusantara Seafood', 'Mitra Udang']
        cities = ['Bekasi', 'Jakarta', 'Karawang', 'Cikarang', 'Tangerang', 'Bogor']
        customers = []
        for i in range(count):
            name = f'{prefixes[i % len(prefixes)]} {names[i % len(names)]} {i + 1:02d}'
            customer, _ = Customer.objects.update_or_create(
                name=name,
                defaults={
                    'phone': f'0812-{1000 + i:04d}-{2000 + i:04d}',
                    'email': f'customer{i + 1:02d}@example.com',
                    'address': f'{cities[i % len(cities)]}, Jawa Barat/DKI',
                },
            )
            customers.append(customer)
        return customers

    def _seed_stocking(self, ponds, base_date):
        for i, pond in enumerate(ponds, start=1):
            if pond.status in ('Budidaya', 'Panen'):
                Stocking.objects.update_or_create(
                    pond=pond,
                    date=base_date - timedelta(days=60 + i),
                    defaults={
                        'seed_count': pond.capacity_seed or 180000,
                        'hatchery': random.choice(['Hatchery Nusantara', 'Global Benur Prima', 'Mina Hatchery']),
                        'notes': 'Data tebar dummy sebagai dasar DOC, SR, biomassa, dan estimasi panen',
                    },
                )

    def _seed_daily_parameters(self, ponds, admin, base_date, count):
        colors = ['Hijau kecoklatan', 'Hijau plankton', 'Coklat muda', 'Cerah kehijauan']
        for i in range(count):
            pond = ponds[i % len(ponds)]
            tanggal = base_date - timedelta(days=i)
            DailyParameter.objects.update_or_create(
                pond=pond,
                date=tanggal,
                defaults={
                    'technician': admin,
                    'doc': 30 + (i % 55),
                    'water_level_cm': Decimal('75.00') + Decimal(i % 36),
                    'temperature': Decimal('28.00') + Decimal(i % 16) / Decimal('10'),
                    'ph_morning': Decimal('7.30') + Decimal(i % 7) / Decimal('10'),
                    'ph_evening': Decimal('7.60') + Decimal(i % 6) / Decimal('10'),
                    'do_morning': Decimal('4.20') + Decimal(i % 14) / Decimal('10'),
                    'do_night': Decimal('3.90') + Decimal(i % 11) / Decimal('10'),
                    'salinity': Decimal('16.00') + Decimal(i % 8),
                    'alkalinity': Decimal('105.00') + Decimal(i % 35),
                    'transparency': Decimal('30.00') + Decimal(i % 16),
                    'feed_kg': Decimal('25.00') + Decimal(i % 35),
                    'mortality': (i * 3) % 120,
                    'water_color': colors[i % len(colors)],
                    'notes': 'Parameter air dummy untuk analisa kondisi kolam dan early warning',
                    'ai_recommendation': 'Pantau DO pagi, stabilkan pH, dan evaluasi pakan berdasarkan anco.',
                },
            )

    def _seed_feed_logs(self, ponds, base_date, count):
        for i in range(count):
            FeedLog.objects.update_or_create(
                pond=ponds[i % len(ponds)],
                date=base_date - timedelta(days=i),
                defaults={
                    'feed_name': f'Pelet 781-{1 + i % 3}',
                    'quantity_kg': Decimal('25.00') + Decimal(i % 35),
                },
            )

    def _seed_treatments(self, ponds, base_date, count):
        treatments = [('Probiotik', '0,2 ppm'), ('Mineral', '1 ppm'), ('Kapur dolomit', '10 ppm'), ('Vitamin C', '5 g/kg pakan')]
        for i in range(count):
            name, dose = treatments[i % len(treatments)]
            Treatment.objects.update_or_create(
                pond=ponds[i % len(ponds)],
                date=base_date - timedelta(days=i),
                name=name,
                defaults={'dose': dose, 'notes': 'Treatment dummy untuk stabilisasi kualitas air dan kesehatan udang'},
            )

    def _seed_daily_pond_records(self, ponds, admin, base_date, count):
        weather = ['Cerah', 'Berawan', 'Hujan', 'Panas', 'Angin Kencang']
        for i in range(count):
            DailyPondRecord.objects.update_or_create(
                pond=ponds[i % len(ponds)],
                date=base_date - timedelta(days=i),
                defaults={
                    'technician': admin,
                    'doc': 30 + (i % 55),
                    'feed_code': f'781-{1 + i % 3}',
                    'daily_feed_kg': Decimal('25.00') + Decimal(i % 35),
                    'water_in_cm': Decimal('2.00') + Decimal(i % 7),
                    'weather': weather[i % len(weather)],
                    'treatment': 'Probiotik + mineral' if i % 5 == 0 else '',
                    'notes': 'Data harian kolam dummy untuk dashboard produksi dan AI Ollama',
                },
            )

    def _seed_anco_checks(self, ponds, admin, base_date, count):
        patterns = [
            ('H', 'H', 'H', 'H', 'H', 'H'),
            ('H', 'H', 'S', 'H', 'H', 'S'),
            ('S', 'S', 'H', 'S', 'H', 'S'),
            ('SS', 'S', 'H', 'SS', 'S', 'H'),
            ('H', 'S', 'H', 'S', 'H', 'H'),
        ]
        for i in range(count):
            p = patterns[i % len(patterns)]
            AncoCheck.objects.update_or_create(
                pond=ponds[i % len(ponds)],
                date=base_date - timedelta(days=i),
                defaults={
                    'technician': admin,
                    'doc': 30 + (i % 55),
                    'anco1_morning': p[0], 'anco2_morning': p[1],
                    'anco1_noon': p[2], 'anco2_noon': p[3],
                    'anco1_evening': p[4], 'anco2_evening': p[5],
                    'notes': 'Cek anco dummy untuk analisa nafsu makan dan rekomendasi pakan harian',
                },
            )

    def _seed_sampling_records(self, ponds, base_date, count):
        made = 0
        week = 0
        active_ponds = ponds[:9]
        while made < count:
            for pond in active_ponds:
                if made >= count:
                    break
                tanggal = base_date - timedelta(days=week * 7)
                doc = 30 + (week * 7) + (made % 5)
                abw = Decimal('2.60') + Decimal(week) * Decimal('0.85') + Decimal(made % 6) / Decimal('10')
                sample_count = 75 + (made % 35)
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
                        'cumulative_feed_kg': Decimal('350.00') + Decimal(made * 12),
                        'stocking_count': tebar,
                        'daily_feed_kg': Decimal('28.00') + Decimal(made % 28),
                        'fr_percent': Decimal('5.50') + Decimal(made % 14) / Decimal('10'),
                        'population_index': int(Decimal(tebar) * (Decimal('0.92') - Decimal(made % 16) / Decimal('100'))),
                        'index_score': Decimal('0.500'),
                        'notes': 'Sampling dummy mengikuti struktur Excel; parameter turunan dihitung otomatis oleh sistem.',
                    },
                )
                made += 1
            week += 1

    def _seed_siphon_records(self, ponds, admin, base_date, count):
        for i in range(count):
            SiphonRecord.objects.update_or_create(
                pond=ponds[i % len(ponds)],
                date=base_date - timedelta(days=i),
                defaults={
                    'technician': admin,
                    'doc': 30 + (i % 55),
                    'dead_count': (i * 5) % 145,
                    'live_count': i % 12,
                    'notes': 'Siphon dummy untuk early warning mortalitas dan indikator kesehatan kolam',
                },
            )

    def _seed_harvests(self, ponds, base_date, count):
        harvests = []
        active_ponds = ponds[:9]
        for i in range(count):
            harvest_type = 'Parsial' if i % 4 else 'Total'
            h, _ = Harvest.objects.update_or_create(
                pond=active_ponds[i % len(active_ponds)],
                date=base_date - timedelta(days=i * 2),
                harvest_type=harvest_type,
                defaults={
                    'size_text': str(random.choice([40, 50, 60, 70, 80, 100])),
                    'total_kg': Decimal('250.00') + Decimal(i * 32),
                    'notes': 'Panen dummy untuk estimasi panen parsial, penjualan, dan laporan investor',
                },
            )
            harvests.append(h)
        return harvests

    def _seed_sales(self, customers, harvests, admin, base_date, count):
        methods = ['Cash', 'Transfer', 'QRIS', 'Midtrans']
        statuses = ['Lunas', 'Lunas', 'Belum Lunas', 'Menunggu Pembayaran']
        for i in range(count):
            customer = customers[i % len(customers)]
            harvest = harvests[i % len(harvests)]
            kg = Decimal('25.00') + Decimal(i % 24) * Decimal('5.00')
            price = Decimal(random.choice([62000, 65000, 68000, 70000, 72000]))
            subtotal = kg * price
            shipping = Decimal('15000') if i % 2 == 0 else Decimal('0')
            packing = Decimal('10000') if i % 3 == 0 else Decimal('0')
            other = Decimal('5000') if i % 5 == 0 else Decimal('0')
            invoice = f'INV/DUMMY/{base_date:%Y%m}/{i + 1:04d}'
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
                    'notes': 'Nota penjualan dummy lengkap dengan biaya opsional dan status pembayaran',
                },
            )
            sale.items.all().delete()
            SaleItem.objects.create(sale=sale, harvest=harvest, size_text=harvest.size_text, weight_kg=kg, price_per_kg=price, subtotal=subtotal)

    def _seed_expenses(self, ponds, base_date, count):
        categories = [c[0] for c in OperationalExpense.CATEGORIES]
        for i in range(count):
            OperationalExpense.objects.update_or_create(
                date=base_date - timedelta(days=i),
                category=categories[i % len(categories)],
                pond=ponds[i % len(ponds)],
                name=f'Biaya {categories[i % len(categories)]} #{i + 1:03d}',
                defaults={
                    'amount': Decimal(random.choice([250000, 500000, 750000, 1250000, 2000000, 3500000])),
                    'payment_method': random.choice(['Cash', 'Transfer', 'QRIS']),
                    'notes': 'Pengeluaran operasional dummy untuk laporan keuangan periodik',
                },
            )

    def _seed_chat_ai(self, users, ponds, count):
        session, _ = ChatSession.objects.get_or_create(
            user=users['admin'],
            pond=ponds[0],
            title='Demo Chat AI Ollama Tambak',
        )
        ChatMessage.objects.get_or_create(session=session, role='user', message='Analisa kondisi Kolam 1 berdasarkan data terbaru.')
        ChatMessage.objects.get_or_create(session=session, role='assistant', message='Kondisi awal terpantau stabil. Pantau DO pagi, cek anco sore, dan evaluasi siphon harian.')
