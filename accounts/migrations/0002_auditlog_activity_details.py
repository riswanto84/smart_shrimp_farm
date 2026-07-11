from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AlterField(model_name="auditlog", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_logs", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="auditlog", name="action_type", field=models.CharField(choices=[("login", "Login"), ("logout", "Logout"), ("create", "Tambah Data"), ("update", "Ubah Data"), ("delete", "Hapus Data"), ("export", "Export/Unduh"), ("access", "Akses"), ("failed", "Gagal"), ("other", "Lainnya")], db_index=True, default="other", max_length=20)),
        migrations.AddField(model_name="auditlog", name="module", field=models.CharField(blank=True, db_index=True, max_length=80)),
        migrations.AddField(model_name="auditlog", name="description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="auditlog", name="object_repr", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="auditlog", name="role_snapshot", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="auditlog", name="method", field=models.CharField(blank=True, max_length=10)),
        migrations.AddField(model_name="auditlog", name="path", field=models.CharField(blank=True, max_length=500)),
        migrations.AddField(model_name="auditlog", name="status_code", field=models.PositiveSmallIntegerField(default=200)),
        migrations.AddField(model_name="auditlog", name="user_agent", field=models.TextField(blank=True)),
        migrations.AddField(model_name="auditlog", name="session_key", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="auditlog", name="metadata", field=models.JSONField(blank=True, default=dict)),
        migrations.AlterField(model_name="auditlog", name="created_at", field=models.DateTimeField(auto_now_add=True, db_index=True)),
        migrations.AlterModelOptions(name="auditlog", options={"ordering": ["-created_at", "-id"]}),
        migrations.AddIndex(model_name="auditlog", index=models.Index(fields=["user", "-created_at"], name="audit_user_created_idx")),
        migrations.AddIndex(model_name="auditlog", index=models.Index(fields=["module", "action_type"], name="audit_module_action_idx")),
    ]
