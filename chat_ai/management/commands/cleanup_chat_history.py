from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from chat_ai.models import ChatSession


class Command(BaseCommand):
    help = 'Menghapus riwayat chat AI sesuai aturan retensi.'

    def handle(self, *args, **options):
        now = timezone.now()
        normal_limit = now - timedelta(days=180)
        error_limit = now - timedelta(days=30)

        normal_deleted, _ = ChatSession.objects.filter(
            retention_type=ChatSession.RETENTION_NORMAL,
            is_important=False,
            created_at__lt=normal_limit,
        ).delete()

        error_deleted, _ = ChatSession.objects.filter(
            retention_type=ChatSession.RETENTION_ERROR,
            is_important=False,
            created_at__lt=error_limit,
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Cleanup selesai. Percakapan biasa dihapus: {normal_deleted}, percakapan error dihapus: {error_deleted}'
            )
        )
