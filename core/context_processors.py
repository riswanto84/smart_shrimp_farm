from django.utils import timezone
import hashlib


def _notification_key(items):
    """Membuat signature stabil untuk notifikasi yang perlu tindakan.

    Signature ini dipakai untuk menandai notifikasi sebagai sudah dibaca.
    Jika isi notifikasi berubah, badge akan muncul kembali.
    """
    attention_items = [i for i in items if i.get('requires_attention')]
    if not attention_items:
        return 'none'
    raw = '|'.join(
        f"{i.get('level','')}:{i.get('title','')}:{i.get('text','')}:{i.get('url','')}"
        for i in attention_items
    )
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]


def app_notifications(request):
    """Notification center topbar admin.

    Best practice yang diterapkan:
    - Badge hanya menghitung notifikasi yang perlu tindakan.
    - Informasi umum tetap tampil sebagai aktivitas terbaru, tetapi tidak menaikkan badge.
    - Status sudah dibaca disimpan di session per signature notifikasi.
    - Jika ada notifikasi baru/berubah, badge muncul kembali otomatis.
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    items = []
    attention_count = 0
    now = timezone.localtime()

    try:
        from sales.models import Sale
        unpaid_count = Sale.objects.filter(status='Belum Lunas').count()
        if unpaid_count:
            attention_count += 1
            items.append({
                'level': 'danger',
                'icon': 'fa-file-invoice-dollar',
                'title': f'{unpaid_count} nota belum lunas',
                'text': 'Segera cek status pembayaran pelanggan pada menu Nota.',
                'meta': 'Penjualan',
                'url': '/sales/invoices/?status=Belum+Lunas',
                'requires_attention': True,
            })
    except Exception:
        pass

    try:
        from operations.models import DailyParameter
        from cultivation.utils import get_selected_cycle
        today = timezone.localdate()
        selected_cycle = get_selected_cycle(request)
        if selected_cycle and selected_cycle.is_open and not DailyParameter.objects.filter(cycle=selected_cycle, date=today).exists():
            attention_count += 1
            items.append({
                'level': 'warning',
                'icon': 'fa-flask-vial',
                'title': 'Parameter harian belum diinput',
                'text': 'Input parameter kolam, pakan, cuaca, air masuk, dan kualitas air hari ini.',
                'meta': 'Parameter harian',
                'url': '/operations/parameters/add/',
                'requires_attention': True,
            })
    except Exception:
        pass

    try:
        from finance.models import OperationalExpense
        expense = OperationalExpense.objects.order_by('-created_at').first()
        if expense:
            items.append({
                'level': 'info',
                'icon': 'fa-wallet',
                'title': 'Pengeluaran terbaru tercatat',
                'text': f'{expense.category}: {expense.name}',
                'meta': 'Keuangan',
                'url': '/finance/expenses/',
                'requires_attention': False,
            })
    except Exception:
        pass

    notification_key = _notification_key(items)
    read_key = request.session.get('ssf_notifications_read_key')
    unread_attention_count = 0 if read_key == notification_key else attention_count

    if not items:
        items.append({
            'level': 'success',
            'icon': 'fa-circle-check',
            'title': 'Tidak ada notifikasi penting',
            'text': 'Semua aktivitas utama sudah aman untuk saat ini.',
            'meta': '',
            'url': '',
            'requires_attention': False,
        })

    return {
        'app_notifications': items[:6],
        'app_notification_count': unread_attention_count,
        'app_notification_total_count': attention_count,
        'app_notification_key': notification_key,
        'app_today': now,
    }


def live_weather(request):
    """Menyediakan cuaca lokasi tambak ke seluruh template terautentikasi."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    try:
        from .weather_service import get_farm_weather
        return {"live_weather": get_farm_weather()}
    except Exception as exc:
        return {
            "live_weather": {
                "ok": False,
                "status": "offline",
                "location": "Muara Gembong",
                "temperature": None,
                "condition": "Data cuaca tidak tersedia",
                "icon": "fa-cloud-circle-exclamation",
                "message": str(exc),
            }
        }
