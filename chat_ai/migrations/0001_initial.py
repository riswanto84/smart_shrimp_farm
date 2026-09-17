from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [('ponds','0001_initial'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='ChatSession', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('title', models.CharField(default='Chat AI Tambak', max_length=150)),('created_at', models.DateTimeField(auto_now_add=True)),('pond', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='ponds.pond')),('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name='ChatMessage', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('role', models.CharField(max_length=20)),('message', models.TextField()),('created_at', models.DateTimeField(auto_now_add=True)),('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat_ai.chatsession'))]),
    ]
