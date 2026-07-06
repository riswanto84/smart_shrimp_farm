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
    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    def __str__(self): return self.action
