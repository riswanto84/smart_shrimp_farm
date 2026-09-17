from django.contrib import admin
from .models import Role, PermissionItem, RolePermission, UserProfile, AuditLog

admin.site.register(Role)
admin.site.register(PermissionItem)
admin.site.register(RolePermission)
admin.site.register(UserProfile)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action_type", "module", "action", "ip_address", "status_code")
    list_filter = ("action_type", "module", "status_code", "created_at")
    search_fields = ("user__username", "user__first_name", "action", "description", "path", "ip_address")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)
    ordering = ("-created_at",)
