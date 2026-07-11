from django.db import migrations, models


def attach_legacy_anco_to_cycle(apps, schema_editor):
    """Kaitkan data Anco lama yang belum memiliki siklus ke siklus pertama.

    Data lama tetap dibiarkan tanpa siklus bila belum ada siklus budidaya.
    """
    AncoCheck = apps.get_model('operations', 'AncoCheck')
    CultivationCycle = apps.get_model('cultivation', 'CultivationCycle')
    cycle = (
        CultivationCycle.objects.filter(status__in=['preparation', 'active', 'harvest'])
        .order_by('-start_date', '-pk')
        .first()
        or CultivationCycle.objects.order_by('-start_date', '-pk').first()
    )
    if cycle is not None:
        AncoCheck.objects.filter(cycle__isnull=True).update(cycle=cycle)


class Migration(migrations.Migration):
    dependencies = [
        ('operations', '0009_add_cultivation_cycle'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='ancocheck',
            unique_together=set(),
        ),
        migrations.RunPython(
            attach_legacy_anco_to_cycle,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name='ancocheck',
            constraint=models.UniqueConstraint(
                fields=('cycle', 'pond', 'date'),
                name='unique_anco_per_cycle_pond_date',
            ),
        ),
    ]
