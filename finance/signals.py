from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AccountReceivable

try:
    from .services import sync_sale_receivable
except ImportError:
    try:
        from .utils import sync_sale_receivable
    except ImportError:
        sync_sale_receivable = None


@receiver(post_save, sender=AccountReceivable)
def keep_sale_status_in_sync(sender, instance, **kwargs):
    """Jadikan saldo piutang sebagai sumber kebenaran status pembayaran nota."""
    if sync_sale_receivable is None:
        return

    sale = getattr(instance, "sale", None)
    if sale is not None:
        sync_sale_receivable(sale)
