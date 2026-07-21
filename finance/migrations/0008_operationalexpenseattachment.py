from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_receipts(apps, schema_editor):
    OperationalExpense = apps.get_model('finance', 'OperationalExpense')
    Attachment = apps.get_model('finance', 'OperationalExpenseAttachment')
    for expense in OperationalExpense.objects.exclude(receipt='').exclude(receipt__isnull=True).iterator():
        name = str(expense.receipt)
        if name and not Attachment.objects.filter(expense_id=expense.pk, file=name).exists():
            Attachment.objects.create(
                expense_id=expense.pk,
                file=name,
                original_name=name.rsplit('/', 1)[-1][:255],
            )


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0007_rename_finance_tra_account_8d922a_idx_finance_tra_account_e9c2ce_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OperationalExpenseAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='expense_attachments/%Y/%m/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('expense', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='finance.operationalexpense', verbose_name='Pengeluaran operasional')),
            ],
            options={'ordering': ['uploaded_at', 'id']},
        ),
        migrations.RunPython(migrate_legacy_receipts, migrations.RunPython.noop),
    ]
