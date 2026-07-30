from django.core.management.base import BaseCommand
from django.urls import reverse
from finance.models import TradeAccount, TradePayment

class Command(BaseCommand):
    help = "Memeriksa instalasi fitur Utang dan Piutang Usaha."

    def handle(self, *args, **options):
        checks = {
            "Model TradeAccount": TradeAccount._meta.db_table,
            "Model TradePayment": TradePayment._meta.db_table,
            "URL Piutang": reverse("finance:receivables"),
            "URL Utang": reverse("finance:payables"),
        }
        for label, value in checks.items():
            self.stdout.write(self.style.SUCCESS(f"OK - {label}: {value}"))
        self.stdout.write(self.style.SUCCESS("Fitur Utang dan Piutang Usaha terpasang."))
