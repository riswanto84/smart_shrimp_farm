from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('cultivation', '0001_initial'),
        ('finance', '0004_backfill_legacy_cycle_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='operationalexpense',
            name='document_number',
            field=models.CharField(blank=True, max_length=80, verbose_name='Nomor bukti'),
        ),
        migrations.AddField(
            model_name='operationalexpense',
            name='is_fiscal_deductible',
            field=models.BooleanField(default=True, verbose_name='Dapat dikurangkan secara fiskal'),
        ),
        migrations.AlterField(
            model_name='operationalexpense',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=16),
        ),
        migrations.AlterField(
            model_name='operationalexpense',
            name='category',
            field=models.CharField(choices=[('Benur','Benur'),('Pakan','Pakan'),('Listrik','Listrik'),('BBM','BBM'),('Obat & Probiotik','Obat & Probiotik'),('Tenaga Kerja','Tenaga Kerja'),('Jasa Pengelola','Jasa Pengelola'),('Peralatan','Peralatan'),('Perbaikan','Perbaikan'),('Transportasi','Transportasi'),('Panen','Panen'),('Administrasi','Administrasi'),('Penyusutan','Penyusutan'),('Pajak','Pajak'),('Lain-lain','Lain-lain')], max_length=50),
        ),
        migrations.CreateModel(
            name='BalanceEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('as_of_date', models.DateField(verbose_name='Tanggal posisi')),
                ('account_type', models.CharField(choices=[('asset','Aset'),('liability','Kewajiban'),('equity','Ekuitas')], max_length=20)),
                ('group', models.CharField(max_length=60)),
                ('account_name', models.CharField(max_length=150)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=16)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering':['account_type','group','account_name']},
        ),
        migrations.CreateModel(
            name='FixedAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=40, unique=True)),
                ('name', models.CharField(max_length=180)),
                ('category', models.CharField(max_length=100)),
                ('acquisition_date', models.DateField()),
                ('use_date', models.DateField()),
                ('acquisition_cost', models.DecimalField(decimal_places=2, max_digits=16)),
                ('additional_cost', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ('residual_value', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ('commercial_useful_life_years', models.PositiveSmallIntegerField(default=4)),
                ('fiscal_group', models.CharField(choices=[('non_depreciable','Tidak disusutkan'),('group_1','Kelompok 1'),('group_2','Kelompok 2'),('group_3','Kelompok 3'),('group_4','Kelompok 4'),('permanent_building','Bangunan Permanen'),('non_permanent_building','Bangunan Tidak Permanen')], default='group_1', max_length=40)),
                ('method', models.CharField(choices=[('straight_line','Garis Lurus')], default='straight_line', max_length=30)),
                ('location', models.CharField(blank=True, max_length=150)),
                ('document_number', models.CharField(blank=True, max_length=80)),
                ('source_of_funds', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('active','Aktif'),('sold','Dijual'),('damaged','Rusak'),('disposed','Dihapuskan')], default='active', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering':['code']},
        ),
        migrations.CreateModel(
            name='OtherRevenue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('document_number', models.CharField(blank=True, max_length=80)),
                ('revenue_type', models.CharField(choices=[('Penjualan hasil sampingan','Penjualan hasil sampingan'),('Jasa','Jasa'),('Pendapatan lain-lain','Pendapatan lain-lain')], default='Pendapatan lain-lain', max_length=60)),
                ('description', models.CharField(max_length=180)),
                ('customer', models.CharField(blank=True, max_length=150)),
                ('gross_amount', models.DecimalField(decimal_places=2, max_digits=16)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=16)),
                ('payment_method', models.CharField(default='Transfer', max_length=30)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cycle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='other_revenues', to='cultivation.cultivationcycle')),
            ],
            options={'ordering':['-date','-id']},
        ),
    ]
