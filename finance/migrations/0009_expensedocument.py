from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('finance', '0008_tradedocument'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='finance/expense_documents/%Y/%m/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('description', models.CharField(blank=True, max_length=180)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('expense', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='finance.operationalexpense')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_expense_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-uploaded_at', '-id']},
        ),
    ]
