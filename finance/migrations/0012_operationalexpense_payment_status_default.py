from django.db import migrations


def ensure_payment_status_default(apps, schema_editor):
    """Set a DB-level default only when the legacy column exists.

    Some production databases contain finance_operationalexpense.payment_status
    as NOT NULL, while the current Django model no longer maps that legacy
    column. PostgreSQL therefore rejects ORM INSERTs that omit it. Keeping a
    database default preserves compatibility without adding a duplicate model
    field or attempting to recreate the existing column.
    """
    connection = schema_editor.connection
    table_name = 'finance_operationalexpense'
    column_name = 'payment_status'

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }
        if column_name not in columns:
            return

        if connection.vendor == 'postgresql':
            qn = connection.ops.quote_name
            cursor.execute(
                f"ALTER TABLE {qn(table_name)} "
                f"ALTER COLUMN {qn(column_name)} SET DEFAULT %s",
                ['paid'],
            )
        elif connection.vendor == 'mysql':
            qn = connection.ops.quote_name
            cursor.execute(
                f"ALTER TABLE {qn(table_name)} MODIFY {qn(column_name)} "
                "varchar(20) NOT NULL DEFAULT %s",
                ['paid'],
            )
        # SQLite is intentionally skipped: its production schema normally does
        # not contain this legacy column, and changing a column default requires
        # rebuilding the table.


def noop_reverse(apps, schema_editor):
    # Do not remove the default on rollback because legacy production code may
    # still depend on it.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0011_operationalexpense_capitalization'),
    ]

    operations = [
        migrations.RunPython(ensure_payment_status_default, noop_reverse),
    ]
