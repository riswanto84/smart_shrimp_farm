from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='CultivationCycle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('start_date', models.DateField(default=django.utils.timezone.localdate)),
                ('target_duration_days', models.PositiveIntegerField(default=135)),
                ('target_end_date', models.DateField(blank=True, null=True)),
                ('actual_end_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('preparation','Persiapan'),('active','Aktif'),('harvest','Panen'),('completed','Selesai')], default='preparation', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-start_date', '-id']},
        ),
    ]
