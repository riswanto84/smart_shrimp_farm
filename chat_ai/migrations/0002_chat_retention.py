from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat_ai', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='model_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='retention_type',
            field=models.CharField(choices=[('important', 'Penting / Simpan Permanen'), ('normal', 'Biasa / Simpan 6 Bulan'), ('error', 'Gagal / Simpan 30 Hari')], default='normal', max_length=20),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='is_important',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='error_message',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='context_snapshot',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
