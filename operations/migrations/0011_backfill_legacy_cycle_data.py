from django.db import migrations


MODEL_NAMES = [
    'Stocking',
    'DailyParameter',
    'Treatment',
    'FeedLog',
    'Harvest',
    'DailyPondRecord',
    'AncoCheck',
    'SamplingRecord',
    'SiphonRecord',
]


def backfill_legacy_cycle_data(apps, schema_editor):
    CultivationCycle = apps.get_model('cultivation', 'CultivationCycle')
    cycle = (
        CultivationCycle.objects.filter(
            status__in=['preparation', 'active', 'harvest']
        ).order_by('-start_date', '-pk').first()
        or CultivationCycle.objects.order_by('-start_date', '-pk').first()
    )
    if cycle is None:
        return

    for model_name in MODEL_NAMES:
        Model = apps.get_model('operations', model_name)
        Model.objects.filter(cycle__isnull=True).update(cycle=cycle)


class Migration(migrations.Migration):
    dependencies = [
        ('cultivation', '0001_initial'),
        ('operations', '0010_anco_unique_per_cycle'),
    ]

    operations = [
        migrations.RunPython(
            backfill_legacy_cycle_data,
            migrations.RunPython.noop,
        ),
    ]
