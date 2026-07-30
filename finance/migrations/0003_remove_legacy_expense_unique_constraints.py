from django.db import migrations


def remove_legacy_unique_constraints(apps, schema_editor):
    """Hapus constraint unik lama pada Pengeluaran Operasional.

    Pengeluaran operasional boleh memiliki lebih dari satu transaksi pada
    kombinasi tanggal/kolam yang sama. Constraint lama dari versi aplikasi
    sebelumnya dapat menyebabkan IntegrityError ketika data kedua disimpan.
    """
    OperationalExpense = apps.get_model('finance', 'OperationalExpense')
    table = OperationalExpense._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table)

    for name, info in constraints.items():
        if not info.get('unique') or info.get('primary_key'):
            continue

        columns = set(info.get('columns') or [])
        # Model ini memang tidak mempunyai unique constraint. Hapus constraint
        # unik warisan yang biasanya memakai date, pond_id, category, atau name.
        if columns & {'date', 'pond_id', 'category', 'name', 'cycle_id'}:
            if connection.vendor == 'postgresql':
                qn = connection.ops.quote_name
                schema_editor.execute(
                    f'ALTER TABLE {qn(table)} DROP CONSTRAINT IF EXISTS {qn(name)}'
                )
            else:
                # Untuk backend non-PostgreSQL, coba melalui schema editor.
                # Tidak melakukan apa-apa bila backend tidak mendukung drop
                # constraint secara langsung; state model tetap tanpa unique.
                try:
                    from django.db import models
                    constraint = models.UniqueConstraint(
                        fields=list(info.get('columns') or []),
                        name=name,
                    )
                    schema_editor.remove_constraint(OperationalExpense, constraint)
                except Exception:
                    pass


def backfill_cycle(apps, schema_editor):
    OperationalExpense = apps.get_model('finance', 'OperationalExpense')
    CultivationCycle = apps.get_model('cultivation', 'CultivationCycle')
    cycle = (
        CultivationCycle.objects.filter(status__in=['preparation', 'active', 'harvest']).first()
        or CultivationCycle.objects.first()
    )
    if cycle:
        OperationalExpense.objects.filter(cycle__isnull=True).update(cycle=cycle)


class Migration(migrations.Migration):
    dependencies = [
        ('cultivation', '0001_initial'),
        ('finance', '0002_add_cycle'),
    ]

    operations = [
        migrations.RunPython(remove_legacy_unique_constraints, migrations.RunPython.noop),
        migrations.RunPython(backfill_cycle, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='operationalexpense',
            options={'ordering': ['-date', '-id']},
        ),
    ]
