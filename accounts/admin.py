from django.contrib import admin
from .models import Role,PermissionItem,RolePermission,UserProfile,AuditLog
admin.site.register(Role); admin.site.register(PermissionItem); admin.site.register(RolePermission); admin.site.register(UserProfile); admin.site.register(AuditLog)
