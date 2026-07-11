from django.db.models import Q

from .models import CultivationCycle


def get_selected_cycle(request, required=False):
    cycle_id = (
        request.POST.get('cycle')
        or request.GET.get('cycle')
        or request.session.get('selected_cycle_id')
    )
    cycle = CultivationCycle.objects.filter(pk=cycle_id).first() if cycle_id else None
    if cycle is None:
        cycle = (
            CultivationCycle.objects.filter(
                status__in=['preparation', 'active', 'harvest']
            ).first()
            or CultivationCycle.objects.first()
        )
    if cycle:
        request.session['selected_cycle_id'] = cycle.pk
    if required and cycle is None:
        raise ValueError('Buat Siklus Budidaya terlebih dahulu sebelum menyimpan data.')
    return cycle


def filter_selected_cycle(request, queryset, include_legacy=True):
    """Filter queryset berdasarkan siklus yang dipilih.

    Selama masa transisi, record lama yang belum mempunyai nilai ``cycle``
    tetap ditampilkan agar data historis tidak tampak hilang dari aplikasi.
    Setelah seluruh data lama berhasil dikaitkan ke siklus, pemanggil dapat
    menggunakan ``include_legacy=False`` bila dibutuhkan.
    """
    cycle = get_selected_cycle(request)
    if cycle is not None and hasattr(queryset.model, 'cycle_id'):
        if include_legacy:
            return queryset.filter(Q(cycle=cycle) | Q(cycle__isnull=True))
        return queryset.filter(cycle=cycle)
    return queryset
