from django.core.management.base import BaseCommand

from core.weather_service import get_farm_weather


class Command(BaseCommand):
    help = "Menguji layanan Weather Card yang sama dengan dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Abaikan cache memori dan ambil data baru dari API.",
        )

    def handle(self, *args, **options):
        result = get_farm_weather(force_refresh=options["refresh"])
        self.stdout.write(f"status       : {result.get('status')}")
        self.stdout.write(f"ok           : {result.get('ok')}")
        self.stdout.write(f"lokasi       : {result.get('location')}")
        self.stdout.write(f"suhu         : {result.get('temperature')} °C")
        self.stdout.write(f"terasa       : {result.get('apparent_temperature')} °C")
        self.stdout.write(f"kelembapan   : {result.get('humidity')} %")
        self.stdout.write(f"peluang hujan: {result.get('rain_chance')} %")
        self.stdout.write(f"angin        : {result.get('wind_speed')} km/jam")
        self.stdout.write(f"tekanan      : {result.get('pressure')} hPa")
        self.stdout.write(f"kondisi      : {result.get('condition')}")
        self.stdout.write(f"diperbarui   : {result.get('updated_at')}")
        self.stdout.write(f"pesan        : {result.get('message')}")
        if result.get("error"):
            self.stderr.write(f"error        : {result['error']}")

        if result.get("temperature") is not None:
            self.stdout.write(self.style.SUCCESS("Weather Card memiliki data yang dapat ditampilkan."))
        else:
            self.stderr.write(self.style.ERROR("Weather Card belum memiliki data yang dapat ditampilkan."))
