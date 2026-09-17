from django.db import migrations


def ensure_supplier_name_default(apps, schema_editor):
    """Make legacy supplier_name compatible with the current ORM model.

    Some production databases still contain
    finance_operationalexpense.supplier_name as a NOT NULL column, although the
    current Django model no longer maps that legacy field. ORM INSERTs therefore
    omit the column and PostgreSQL rejects the row. A database-level empty-string
    default preserves all existing data and keeps both old and current schemas
    usable without reintroducing a duplicate form field.
    """
    connection = schema_editor.connection
    table_name = 'finance_operationalexpense'
    column_name = 'supplier_name'

    with connection.cursor() as cursor:
        try:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, table_name
                )
            }
        except Exception:
            # The table may not exist in a brand-new or partial installation.
            return

        if column_name not in columns:
            return

        qn = connection.ops.quote_name

        if connection.vendor == 'postgresql':
            cursor.execute(
                f"ALTER TABLE {qn(table_name)} "
                f"ALTER COLUMN {qn(column_name)} SET DEFAULT %s",
                [''],
            )
            # Repair legacy rows if the column was temporarily nullable.
            cursor.execute(
                f"UPDATE {qn(table_name)} SET {qn(column_name)} = %s "
                f"WHERE {qn(column_name)} IS NULL",
                [''],
            )
            cursor.execute(
                f"ALTER TABLE {qn(table_name)} "
                f"ALTER COLUMN {qn(column_name)} SET NOT NULL"
            )
        elif connection.vendor == 'mysql':
            cursor.execute(
                f"UPDATE {qn(table_name)} SET {qn(column_name)} = %s "
                f"WHERE {qn(column_name)} IS NULL",
                [''],
            )
            cursor.execute(
                f"ALTER TABLE {qn(table_name)} MODIFY {qn(column_name)} "
                "varchar(255) NOT NULL DEFAULT %s",
                [''],
            )
        # SQLite is normally unaffected because the legacy column is absent.
        # Rebuilding its table solely to alter a default would be unnecessarily
        # invasive, so it is intentionally skipped.


def noop_reverse(apps, schema_editor):
    # Keep the compatibility default during rollback; older production code may
    # still rely on this legacy column.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0013_biologicalassetvaluation'),
    ]

    operations = [
        migrations.RunPython(ensure_supplier_name_default, noop_reverse),
    ]
