from __future__ import annotations

from typing import Any
from django.contrib.auth.models import AnonymousUser
from .models import AuditLog

SENSITIVE_KEYS = {"password", "password1", "password2", "old_password", "new_password1", "new_password2", "csrfmiddlewaretoken", "token", "secret", "server_key", "client_key"}


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def role_label(user):
    if not user or isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        return "Tidak terautentikasi"
    if user.is_superuser:
        return "Root / Superuser"
    try:
        roles = list(user.userprofile.roles.values_list("name", flat=True))
        return ", ".join(roles) if roles else ("Administrator" if user.is_staff else "User")
    except Exception:
        return "Administrator" if user.is_staff else "User"


def safe_post_snapshot(request):
    result = {}
    for key in request.POST.keys():
        lowered = key.lower()
        if lowered in SENSITIVE_KEYS or "password" in lowered or "token" in lowered or "secret" in lowered:
            continue
        values = request.POST.getlist(key)
        cleaned = [str(v)[:200] for v in values if str(v).strip()]
        if cleaned:
            result[key] = cleaned if len(cleaned) > 1 else cleaned[0]
    return result


def log_activity(request, *, action, action_type="other", module="", description="", object_repr="", status_code=200, metadata=None, user=None):
    actor = user if user is not None else getattr(request, "user", None)
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    try:
        log = AuditLog.objects.create(
            user=actor,
            action=str(action)[:255],
            action_type=action_type,
            module=str(module)[:80],
            description=description,
            object_repr=str(object_repr)[:255],
            role_snapshot=role_label(actor),
            method=getattr(request, "method", "")[:10],
            path=getattr(request, "path", "")[:500],
            status_code=int(status_code or 200),
            ip_address=client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
            session_key=getattr(getattr(request, "session", None), "session_key", "") or "",
            metadata=metadata or {},
        )
        request._activity_logged = True
        return log
    except Exception:
        # Log audit tidak boleh menggagalkan transaksi utama aplikasi.
        return None
