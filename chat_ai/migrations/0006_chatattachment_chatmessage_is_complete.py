# Generated for Smart Shrimp AI streaming and file attachments.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('chat_ai', '0005_alter_chatmessage_role')]
    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='is_complete',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='ChatAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='chat_ai/%Y/%m/%d/')),
                ('original_name', models.CharField(max_length=255)),
                ('content_type', models.CharField(blank=True, max_length=120)),
                ('size', models.PositiveBigIntegerField(default=0)),
                ('extracted_text', models.TextField(blank=True)),
                ('extraction_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='chat_ai.chatmessage')),
            ],
        ),
    ]
