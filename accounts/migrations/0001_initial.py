# Generated manually for SMART SHRIMP FARM
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('name', models.CharField(max_length=50, unique=True)),('description', models.TextField(blank=True))],
        ),
        migrations.CreateModel(
            name='PermissionItem',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('code', models.CharField(max_length=100, unique=True)),('name', models.CharField(max_length=150)),('group', models.CharField(blank=True, max_length=80))],
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('action', models.CharField(max_length=255)),('created_at', models.DateTimeField(auto_now_add=True)),('ip_address', models.GenericIPAddressField(blank=True, null=True)),('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL))],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('phone', models.CharField(blank=True, max_length=30)),('is_online', models.BooleanField(default=False)),('roles', models.ManyToManyField(blank=True, to='accounts.role')),('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))],
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.permissionitem')),('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.role'))],
            options={'unique_together': {('role', 'permission')}},
        ),
    ]
