from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('cultivation','0001_initial'),('sales','0004_alter_sale_payment_method_alter_sale_status')]
    operations=[migrations.AddField(model_name='sale',name='cycle',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='sales',to='cultivation.cultivationcycle'))]
