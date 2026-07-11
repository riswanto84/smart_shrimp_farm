from __future__ import annotations

from .activity import log_activity, safe_post_snapshot

MODULE_LABELS = {
    "accounts": "Pengguna & Hak Akses",
    "cycles": "Siklus Budidaya",
    "cultivation": "Siklus Budidaya",
    "ponds": "Master Kolam",
    "operations": "Operasional Tambak",
    "sales": "Penjualan",
    "finance": "Keuangan",
    "investor": "Investor",
    "weather": "Prakiraan Cuaca",
    "chat-ai": "AI Tambak",
    "dashboard": "Dashboard",
    "admin": "Django Admin",
}

EXCLUDED_PREFIXES = (
    "/static/", "/media/", "/favicon.ico", "/accounts/activity/",
)
MANUAL_PATH_PREFIXES = (
    "/accounts/login/", "/accounts/logout/", "/accounts/users/",
    "/accounts/profile/", "/accounts/password/",
)


def module_from_path(path):
    first = path.strip("/").split("/", 1)[0] if path.strip("/") else "dashboard"
    return MODULE_LABELS.get(first, first.replace("-", " ").title() or "Dashboard")


def action_from_request(request):
    path = request.path.lower()
    if any(word in path for word in ("export", "download", "pdf", "excel")):
        return "export", "Mengunduh atau mengekspor data"
    if any(word in path for word in ("delete", "hapus")) or request.method == "DELETE":
        return "delete", "Menghapus data"
    if any(word in path for word in ("edit", "update", "ubah")) or request.method in {"PUT", "PATCH"}:
        return "update", "Mengubah data"
    if any(word in path for word in ("add", "create", "tambah")) or request.method == "POST":
        return "create", "Menambahkan atau memproses data"
    return "access", "Mengakses fitur"


class ActivityLogMiddleware:
    """Mencatat aksi perubahan data yang berhasil tanpa menyimpan password/secret."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if not getattr(request, "user", None) or not request.user.is_authenticated:
                return response
            if getattr(request, "_activity_logged", False):
                return response
            if request.path.startswith(EXCLUDED_PREFIXES) or request.path.startswith(MANUAL_PATH_PREFIXES):
                return response
            should_log = request.method in {"POST", "PUT", "PATCH", "DELETE"}
            should_log = should_log or (request.method == "GET" and any(x in request.path.lower() for x in ("export", "download", "/pdf", "/excel")))
            if not should_log:
                return response
            action_type, description = action_from_request(request)
            if response.status_code >= 400:
                action_type = "failed"
                description = f"Aksi gagal dengan HTTP {response.status_code}"
            metadata = {"query": request.GET.dict()}
            if request.method == "POST":
                metadata["form"] = safe_post_snapshot(request)
            log_activity(
                request,
                action=f"{description} pada {module_from_path(request.path)}",
                action_type=action_type,
                module=module_from_path(request.path),
                description=description,
                status_code=response.status_code,
                metadata=metadata,
            )
        except Exception:
            pass
        return response
