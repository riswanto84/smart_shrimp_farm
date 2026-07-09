from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

ROLE_PERMISSIONS = {
    'owner': {'all'},
    'owner tambak': {'all'},
    'admin': {'all'},
    'admin tambak': {'all'},
    'super admin': {'all'},
    'teknisi': {
        'dashboard', 'ponds.view', 'operations.production_dashboard', 'operations.parameter_dashboard',
        'operations.anco', 'operations.sampling', 'operations.siphon', 'operations.parameters',
        'operations.harvests', 'weather.view', 'chat.view'
    },
    'kasir': {
        'dashboard', 'sales.dashboard', 'sales.cashier', 'sales.invoices', 'sales.customers'
    },
    'akuntan': {
        'dashboard', 'sales.dashboard', 'sales.invoices', 'finance.expenses', 'finance.profit_loss', 'finance.periodic_report'
    },
    'investor': {
        'dashboard', 'investor.dashboard'
    },
}

MENU_DEFINITIONS = [
    {'type': 'item', 'label': 'Dashboard', 'url': '/dashboard/', 'icon': 'fa-solid fa-house', 'perm': 'dashboard'},
    {'type': 'group', 'label': 'OPERASIONAL'},
    {'type': 'item', 'label': 'Master Kolam', 'url': '/ponds/', 'icon': 'fa-solid fa-water', 'perm': 'ponds.view'},
    {'type': 'item', 'label': 'Dashboard Produksi', 'url': '/operations/production-dashboard/', 'icon': 'fa-solid fa-chart-line', 'perm': 'operations.production_dashboard'},
    {'type': 'item', 'label': 'Dashboard Parameter Harian', 'url': '/operations/parameter-dashboard/', 'icon': 'fa-solid fa-chart-simple', 'perm': 'operations.parameter_dashboard'},
    {'type': 'item', 'label': 'Cek Anco Harian', 'url': '/operations/anco/', 'icon': 'fa-solid fa-clipboard-check', 'perm': 'operations.anco'},
    {'type': 'item', 'label': 'Data Sampling', 'url': '/operations/sampling/', 'icon': 'fa-solid fa-weight-scale', 'perm': 'operations.sampling'},
    {'type': 'item', 'label': 'Data Siphon', 'url': '/operations/siphon/', 'icon': 'fa-solid fa-water-ladder', 'perm': 'operations.siphon'},
    {'type': 'item', 'label': 'Input Parameter Harian', 'url': '/operations/parameters/', 'icon': 'fa-solid fa-flask-vial', 'perm': 'operations.parameters'},
    {'type': 'item', 'label': 'Panen', 'url': '/operations/harvests/', 'icon': 'fa-solid fa-shrimp', 'perm': 'operations.harvests'},
    {'type': 'group', 'label': 'PENJUALAN'},
    {'type': 'item', 'label': 'Dashboard Penjualan', 'url': '/sales/dashboard/', 'icon': 'fa-solid fa-chart-pie', 'perm': 'sales.dashboard'},
    {'type': 'item', 'label': 'Kasir Penjualan', 'url': '/sales/cashier/', 'icon': 'fa-solid fa-cash-register', 'perm': 'sales.cashier'},
    {'type': 'item', 'label': 'Nota', 'url': '/sales/invoices/', 'icon': 'fa-solid fa-file-invoice-dollar', 'perm': 'sales.invoices'},
    {'type': 'item', 'label': 'Pelanggan', 'url': '/sales/customers/', 'icon': 'fa-solid fa-users', 'perm': 'sales.customers'},
    {'type': 'group', 'label': 'KEUANGAN'},
    {'type': 'item', 'label': 'Pengeluaran Operasional', 'url': '/finance/expenses/', 'icon': 'fa-solid fa-wallet', 'perm': 'finance.expenses'},
    {'type': 'item', 'label': 'Laba Rugi', 'url': '/finance/profit-loss/', 'icon': 'fa-solid fa-chart-line', 'perm': 'finance.profit_loss'},
    {'type': 'item', 'label': 'Laporan Keuangan Periodik', 'url': '/finance/periodic-report/', 'icon': 'fa-solid fa-chart-column', 'perm': 'finance.periodic_report'},
    {'type': 'group', 'label': 'LAINNYA'},
    {'type': 'item', 'label': 'Dashboard Investor', 'url': '/investor/dashboard/', 'icon': 'fa-solid fa-building-columns', 'perm': 'investor.dashboard'},
    {'type': 'item', 'label': 'Prakiraan Cuaca', 'url': '/weather/', 'icon': 'fa-solid fa-cloud-sun', 'perm': 'weather.view'},
    {'type': 'group', 'label': 'AI TAMBAK'},
    {'type': 'item', 'label': 'AI Analisa Kolam', 'url': '/chat-ai/pond-analysis/', 'icon': 'fa-solid fa-wand-magic-sparkles', 'perm': 'chat.view'},
    {'type': 'item', 'label': 'AI Rekomendasi Pakan', 'url': '/chat-ai/feed-recommendation/', 'icon': 'fa-solid fa-bowl-food', 'perm': 'chat.view'},
    {'type': 'item', 'label': 'AI Early Warning', 'url': '/chat-ai/siphon-warning/', 'icon': 'fa-solid fa-triangle-exclamation', 'perm': 'chat.view'},
    {'type': 'item', 'label': 'AI Prediksi Panen', 'url': '/chat-ai/harvest-prediction/', 'icon': 'fa-solid fa-calendar-check', 'perm': 'chat.view'},
    {'type': 'item', 'label': 'AI Ringkasan Harian', 'url': '/chat-ai/daily-summary/', 'icon': 'fa-solid fa-file-lines', 'perm': 'chat.view'},
    {'type': 'item', 'label': 'Chat AI (Ollama)', 'url': '/chat-ai/', 'icon': 'fa-solid fa-robot', 'perm': 'chat.view'},
    {'type': 'group', 'label': 'AKUN'},
    {'type': 'item', 'label': 'Edit Profil', 'url': '/accounts/profile/', 'icon': 'fa-solid fa-user-pen', 'perm': 'dashboard'},
    {'type': 'item', 'label': 'Ubah Password', 'url': '/accounts/password/', 'icon': 'fa-solid fa-lock', 'perm': 'dashboard'},
    {'type': 'group', 'label': 'PENGATURAN'},
    {'type': 'item', 'label': 'Pengguna & Hak Akses', 'url': '/accounts/users/', 'icon': 'fa-solid fa-user-shield', 'perm': 'accounts.users'},
    {'type': 'item', 'label': 'Role & Permission', 'url': '/accounts/roles/', 'icon': 'fa-solid fa-key', 'perm': 'accounts.roles'},
]

BOTTOM_MENU_DEFINITIONS = [
    {'label': 'Dashboard', 'url': '/dashboard/', 'icon': 'fa-solid fa-gauge-high', 'perm': 'dashboard'},
    {'label': 'Produksi', 'url': '/operations/production-dashboard/', 'icon': 'fa-solid fa-chart-line', 'perm': 'operations.production_dashboard'},
    {'label': 'Kasir', 'url': '/sales/cashier/', 'icon': 'fa-solid fa-receipt', 'perm': 'sales.cashier'},
    {'label': 'Pelanggan', 'url': '/sales/customers/', 'icon': 'fa-solid fa-users', 'perm': 'sales.customers'},
    {'label': 'Investor', 'url': '/investor/dashboard/', 'icon': 'fa-solid fa-building-columns', 'perm': 'investor.dashboard'},
    {'label': 'AI', 'url': '/chat-ai/', 'icon': 'fa-solid fa-robot', 'perm': 'chat.view'},
]

def normalized_roles(user):
    if not user.is_authenticated:
        return []
    if user.is_superuser:
        return ['owner']
    try:
        return [r.strip().lower() for r in user.userprofile.roles.values_list('name', flat=True)]
    except Exception:
        return []

def has_permission(user, permission_code):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Django staff tetap dibatasi oleh role aplikasi, kecuali belum ada role: staff dianggap admin agar tidak terkunci.
    roles = normalized_roles(user)
    if not roles and user.is_staff:
        roles = ['admin']
    for role in roles:
        perms = ROLE_PERMISSIONS.get(role, set())
        if 'all' in perms or permission_code in perms:
            return True
    return False

def permission_required(permission_code):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if has_permission(request.user, permission_code):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Akses ditolak. Role Anda tidak memiliki izin membuka fitur tersebut.')
            return render(request, 'accounts/forbidden.html', status=403)
        return wrapper
    return decorator

def visible_menu(user):
    result = []
    pending_group = None
    for item in MENU_DEFINITIONS:
        if item['type'] == 'group':
            pending_group = item
            continue
        if has_permission(user, item['perm']):
            if pending_group:
                result.append(pending_group)
                pending_group = None
            result.append(item)
    return result

def visible_bottom_menu(user):
    return [i for i in BOTTOM_MENU_DEFINITIONS if has_permission(user, i['perm'])][:5]

def primary_role_label(user):
    if not user.is_authenticated:
        return ''
    if user.is_superuser:
        return 'Owner'
    try:
        names = list(user.userprofile.roles.values_list('name', flat=True))
        return ', '.join(names) if names else ('Administrator' if user.is_staff else 'User')
    except Exception:
        return 'User'
