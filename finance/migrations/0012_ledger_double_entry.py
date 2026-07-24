from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0011_operationalexpense_capitalization'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LedgerAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=150)),
                ('account_type', models.CharField(choices=[('asset','Aset'),('liability','Kewajiban'),('equity','Ekuitas'),('revenue','Pendapatan'),('expense','Beban')], max_length=20)),
                ('normal_balance', models.CharField(choices=[('debit','Debit'),('credit','Kredit')], max_length=10)),
                ('group', models.CharField(blank=True, max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('is_system', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True)),
            ],
            options={'ordering':['code']},
        ),
        migrations.CreateModel(
            name='JournalEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('reference', models.CharField(blank=True, db_index=True, max_length=100)),
                ('description', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('draft','Draft'),('posted','Diposting'),('void','Dibatalkan')], default='posted', max_length=10)),
                ('source_type', models.CharField(blank=True, db_index=True, max_length=50)),
                ('source_id', models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
                ('is_system_generated', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('posted_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='finance_journal_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-date','-id']},
        ),
        migrations.CreateModel(
            name='JournalLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=255)),
                ('debit', models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ('credit', models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='journal_lines', to='finance.ledgeraccount')),
                ('entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='finance.journalentry')),
            ],
            options={'ordering':['entry_id','id']},
        ),
        migrations.AddConstraint(
            model_name='journalentry',
            constraint=models.UniqueConstraint(condition=models.Q(('is_system_generated', True)), fields=('source_type','source_id'), name='uniq_system_journal_source'),
        ),
    ]
