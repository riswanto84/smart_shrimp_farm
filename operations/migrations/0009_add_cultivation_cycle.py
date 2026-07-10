from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('cultivation','0001_initial'),('operations','0008_ancocheck_lapangan_fields')]
    operations=[
      migrations.AddField(model_name=n,name='cycle',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name=f'{n}_records',to='cultivation.cultivationcycle'))
      for n in ['stocking','dailyparameter','treatment','feedlog','harvest','dailypondrecord','ancocheck','samplingrecord','siphonrecord']
    ]
