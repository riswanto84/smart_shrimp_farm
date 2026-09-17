from django.db import migrations


def backfill_legacy_cycle_data(apps, schema_editor):
    CultivationCycle = apps.get_model('cultivation', 'CultivationCycle')
    OperationalExpense = apps.get_model('finance', 'OperationalExpense')
    cycle = (
        CultivationCycle.objects.filter(
            status__in=['preparation', 'active', 'harvest']
        ).order_by('-start_date', '-pk').first()
        or CultivationCycle.objects.order_by('-start_date', '-pk').first()
    )
    if cycle is not None:
        OperationalExpense.objects.filter(cycle__isnull=True).update(cycle=cycle)


class Migration(migrations.Migration):
    dependencies = [
        ('cultivation', '0001_initial'),
        ('finance', '0003_remove_legacy_expense_unique_constraints'),
    ]

    operations = [
        migrations.RunPython(
            backfill_legacy_cycle_data,
            migrations.RunPython.noop,
        ),
    ]
