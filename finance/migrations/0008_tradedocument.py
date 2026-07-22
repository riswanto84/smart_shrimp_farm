from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('finance', '0007_rename_finance_tra_account_8d922a_idx_finance_tra_account_e9c2ce_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TradeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='finance/trade_documents/%Y/%m/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('description', models.CharField(blank=True, max_length=180)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='finance.tradepayment')),
                ('trade_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='finance.tradeaccount')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_trade_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-uploaded_at', '-id']},
        ),
    ]
