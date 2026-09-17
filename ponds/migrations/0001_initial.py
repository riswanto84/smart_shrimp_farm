from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Pond',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('area_m2', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('depth_m', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('capacity_seed', models.IntegerField(default=0)),
                ('pond_type', models.CharField(blank=True, max_length=80)),
                ('status', models.CharField(choices=[('Persiapan', 'Persiapan'), ('Budidaya', 'Budidaya'), ('Panen', 'Panen'), ('Kosong', 'Kosong'), ('Perbaikan', 'Perbaikan')], default='Persiapan', max_length=20)),
                ('location', models.CharField(blank=True, max_length=150)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='ponds/')),
                ('notes', models.TextField(blank=True)),
            ],
        ),
    ]
