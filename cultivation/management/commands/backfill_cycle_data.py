from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from cultivation.models import CultivationCycle


TARGET_MODELS = [
    ('operations', 'Stocking'),
    ('operations', 'DailyParameter'),
    ('operations', 'Treatment'),
    ('operations', 'FeedLog'),
    ('operations', 'Harvest'),
    ('operations', 'DailyPondRecord'),
    ('operations', 'AncoCheck'),
    ('operations', 'SamplingRecord'),
    ('operations', 'SiphonRecord'),
    ('finance', 'OperationalExpense'),
    ('sales', 'Sale'),
    ('chat_ai', 'ChatSession'),
]


class Command(BaseCommand):
    help = 'Mengaitkan data lama yang cycle-nya kosong ke satu Siklus Budidaya.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cycle-id',
            type=int,
            help='ID siklus tujuan. Jika kosong, memakai siklus aktif/terbuka terbaru.',
        )

    def handle(self, *args, **options):
        cycle_id = options.get('cycle_id')
        if cycle_id:
            cycle = CultivationCycle.objects.filter(pk=cycle_id).first()
        else:
            cycle = (
                CultivationCycle.objects.filter(
                    status__in=['preparation', 'active', 'harvest']
                ).order_by('-start_date', '-pk').first()
                or CultivationCycle.objects.order_by('-start_date', '-pk').first()
            )

        if cycle is None:
            raise CommandError('Belum ada Siklus Budidaya. Buat siklus terlebih dahulu.')

        total = 0
        for app_label, model_name in TARGET_MODELS:
            Model = apps.get_model(app_label, model_name)
            count = Model.objects.filter(cycle__isnull=True).update(cycle=cycle)
            total += count
            self.stdout.write(f'{app_label}.{model_name}: {count} data diperbarui')

        self.stdout.write(
            self.style.SUCCESS(
                f'Selesai. Total {total} data lama dikaitkan ke siklus "{cycle.name}".'
            )
        )
