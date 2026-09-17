from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('cultivation', '0001_initial')]
    operations = [
        migrations.AddField(
            model_name='cultivationcycle',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cultivationcycle',
            name='final_snapshot',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
