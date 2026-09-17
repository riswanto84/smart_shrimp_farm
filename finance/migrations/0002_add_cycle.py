from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('cultivation','0001_initial'),('finance','0001_initial')]
    operations=[migrations.AddField(model_name='operationalexpense',name='cycle',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='expenses',to='cultivation.cultivationcycle'))]
