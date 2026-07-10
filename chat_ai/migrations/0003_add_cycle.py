from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('cultivation','0001_initial'),('chat_ai','0002_chat_retention')]
    operations=[migrations.AddField(model_name='chatsession',name='cycle',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='chat_sessions',to='cultivation.cultivationcycle'))]
