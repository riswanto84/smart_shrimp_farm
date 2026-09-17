from django.db import migrations


def make_legacy_attachment_cascade(apps, schema_editor):
    """Make the legacy expense attachment FK cascade on PostgreSQL.

    Older production databases can still have
    finance_operationalexpenseattachment. The current application no longer
    maps that table, so Django migrations do not manage its FK. Rebuild any
    FK from that table's expense_id column to finance_operationalexpense(id)
    with ON DELETE CASCADE, while leaving fresh installations untouched.
    """
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class child ON child.oid = c.conrelid
            JOIN pg_class parent ON parent.oid = c.confrelid
            WHERE child.relname = 'finance_operationalexpenseattachment'
              AND parent.relname = 'finance_operationalexpense'
              AND c.contype = 'f'
            """
        )
        constraints = [row[0] for row in cursor.fetchall()]
        if not constraints:
            return

        qn = connection.ops.quote_name
        for name in constraints:
            cursor.execute(
                f'ALTER TABLE {qn("finance_operationalexpenseattachment")} '
                f'DROP CONSTRAINT {qn(name)}'
            )

        cursor.execute(
            f'ALTER TABLE {qn("finance_operationalexpenseattachment")} '
            'ADD CONSTRAINT finance_operationale_expense_id_fk '
            f'FOREIGN KEY ({qn("expense_id")}) '
            f'REFERENCES {qn("finance_operationalexpense")} ({qn("id")}) '
            'ON DELETE CASCADE'
        )


def noop_reverse(apps, schema_editor):
    # Keep CASCADE in place on rollback. The legacy table is outside the
    # current Django model graph and restoring its previous FK action would be
    # unsafe/ambiguous.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0015_operationalexpense_trade_payment_cash_basis'),
    ]

    operations = [
        migrations.RunPython(make_legacy_attachment_cascade, noop_reverse),
    ]
