from django.core.management.base import BaseCommand

from core.weather_service import get_farm_weather


class Command(BaseCommand):
    help = "Menguji koneksi Weather API dari environment Django yang sedang aktif."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Abaikan cache dan ambil data baru dari API.",
        )

    def handle(self, *args, **options):
        result = get_farm_weather(force_refresh=options["refresh"])
        self.stdout.write(f"status      : {result.get('status')}")
        self.stdout.write(f"ok          : {result.get('ok')}")
        self.stdout.write(f"lokasi      : {result.get('location')}")
        self.stdout.write(f"suhu        : {result.get('temperature')}")
        self.stdout.write(f"kondisi     : {result.get('condition')}")
        self.stdout.write(f"diperbarui  : {result.get('updated_at')}")
        self.stdout.write(f"pesan       : {result.get('message')}")
        if result.get("error"):
            self.stderr.write(f"error       : {result['error']}")

        if result.get("ok"):
            self.stdout.write(self.style.SUCCESS("Weather API berhasil diakses."))
        else:
            self.stderr.write(self.style.ERROR("Weather API belum dapat diakses."))
