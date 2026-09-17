from .models import CultivationCycle
from .utils import get_selected_cycle


def cultivation_cycle_context(request):
    """Sediakan siklus terpilih dan status kunci pada seluruh template.

    Selalu memakai helper yang sama dengan view agar pilihan pada GET/POST/session
    tidak berbeda antara backend dan tampilan.
    """
    cycles = CultivationCycle.objects.all()
    selected = get_selected_cycle(request)
    locked = bool(selected and selected.status == CultivationCycle.STATUS_COMPLETED)
    return {
        'cultivation_cycles': cycles,
        'selected_cycle': selected,
        'cycle_is_locked': locked,
        'cycle_is_open': bool(selected and not locked),
    }
