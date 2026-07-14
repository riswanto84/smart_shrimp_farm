from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .models import CultivationCycle
from .utils import get_selected_cycle


def cycle_write_guard(view_func):
    """Blokir add/edit/delete/import ketika siklus terkait sudah selesai.

    Untuk edit/hapus, siklus milik record diprioritaskan. Untuk tambah/import,
    siklus yang sedang dipilih digunakan. Dengan demikian URL langsung pun aman.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        cycle = None
        pk = kwargs.get('pk')
        name = view_func.__name__

        if pk:
            try:
                from operations.models import (
                    DailyPondRecord, AncoCheck, SamplingRecord,
                    SiphonRecord, DailyParameter, Harvest,
                )
                model_map = {
                    'edit_daily_record': DailyPondRecord,
                    'delete_daily_record': DailyPondRecord,
                    'edit_anco_check': AncoCheck,
                    'delete_anco_check': AncoCheck,
                    'edit_sampling_record': SamplingRecord,
                    'delete_sampling_record': SamplingRecord,
                    'edit_siphon_record': SiphonRecord,
                    'delete_siphon_record': SiphonRecord,
                    'edit_parameter': DailyParameter,
                    'delete_parameter': DailyParameter,
                    'edit_harvest': Harvest,
                    'delete_harvest': Harvest,
                }
                model = model_map.get(name)
                if model:
                    obj = model.objects.filter(pk=pk).select_related('cycle').first()
                    cycle = getattr(obj, 'cycle', None)
            except Exception:
                cycle = None

        cycle = cycle or get_selected_cycle(request)
        if cycle and cycle.status == CultivationCycle.STATUS_COMPLETED:
            messages.warning(
                request,
                f'{cycle.name} sudah selesai. Data operasional dikunci dan hanya dapat dilihat atau diekspor.'
            )
            fallback = {
                'parameter': 'operations:parameters',
                'anco': 'operations:anco_checks',
                'sampling': 'operations:sampling_records',
                'siphon': 'operations:siphon_records',
                'daily': 'operations:daily_records',
                'harvest': 'operations:harvests',
            }
            module = kwargs.get('module', '')
            if module in fallback:
                return redirect(reverse(fallback[module]))
            if 'parameter' in name:
                return redirect(reverse('operations:parameters'))
            if 'anco' in name:
                return redirect(reverse('operations:anco_checks'))
            if 'sampling' in name:
                return redirect(reverse('operations:sampling_records'))
            if 'siphon' in name:
                return redirect(reverse('operations:siphon_records'))
            if 'daily' in name:
                return redirect(reverse('operations:daily_records'))
            if 'harvest' in name:
                return redirect(reverse('operations:harvests'))
            return redirect(reverse('cultivation:list'))
        return view_func(request, *args, **kwargs)
    return wrapped
