from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .utils import get_selected_cycle


class CycleWriteLockMiddleware:
    """Kunci seluruh perubahan data operasional ketika siklus terpilih selesai.

    Penguncian diterapkan di server, bukan hanya menyembunyikan tombol UI, sehingga
    URL add/edit/delete/import tidak dapat dipakai untuk mengubah arsip siklus.
    """

    WRITE_URL_NAMES = {
        'add_parameter', 'edit_parameter', 'delete_parameter',
        'add_daily_record', 'edit_daily_record', 'delete_daily_record',
        'add_anco_check', 'edit_anco_check', 'delete_anco_check',
        'add_sampling_record', 'edit_sampling_record', 'delete_sampling_record',
        'add_siphon_record', 'edit_siphon_record', 'delete_siphon_record',
        'add_harvest', 'edit_harvest', 'delete_harvest',
        'import_excel',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        match = getattr(request, 'resolver_match', None)
        if request.user.is_authenticated and match and match.namespace == 'operations':
            if match.url_name in self.WRITE_URL_NAMES:
                cycle = get_selected_cycle(request)
                if cycle and not cycle.is_open:
                    messages.warning(
                        request,
                        f'{cycle.name} sudah selesai dan telah dikunci. '
                        'Data hanya dapat dilihat atau diekspor. Buat dan pilih siklus baru untuk mulai input.',
                    )
                    return redirect(reverse('cultivation:list'))
        return self.get_response(request)
