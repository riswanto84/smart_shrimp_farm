from django.db import models
from django.contrib.auth.models import User

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    def __str__(self): return self.name

class PermissionItem(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    group = models.CharField(max_length=80, blank=True)
    def __str__(self): return self.code

class RolePermission(models.Model):
    role = models.ForeignKey(Role,on_delete=models.CASCADE)
    permission = models.ForeignKey(PermissionItem,on_delete=models.CASCADE)
    class Meta: unique_together=('role','permission')

class UserProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, blank=True)
    roles = models.ManyToManyField(Role, blank=True)
    is_online = models.BooleanField(default=False)
    def __str__(self): return self.user.username

class AuditLog(models.Model):
    ACTION_TYPES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("create", "Tambah Data"),
        ("update", "Ubah Data"),
        ("delete", "Hapus Data"),
        ("export", "Export/Unduh"),
        ("access", "Akses"),
        ("failed", "Gagal"),
        ("other", "Lainnya"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=255)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default="other", db_index=True)
    module = models.CharField(max_length=80, blank=True, db_index=True)
    description = models.TextField(blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    role_snapshot = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=500, blank=True)
    status_code = models.PositiveSmallIntegerField(default=200)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="audit_user_created_idx"),
            models.Index(fields=["module", "action_type"], name="audit_module_action_idx"),
        ]

    def __str__(self):
        return self.action
