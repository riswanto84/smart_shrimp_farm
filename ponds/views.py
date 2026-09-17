from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.rbac import permission_required
from core.pagination import paginate_queryset
from .models import Pond


def _clean_decimal_id(value, field_key, field_label, errors, *, default=Decimal('0'), min_value=Decimal('0')):
    """Validasi ketat angka desimal HTML: 1825 / 1825.00 / 1.45."""
    raw = (value or '').strip()
    if raw == '':
        return default

    # Field ini harus berupa angka murni dari input type=number.
    # Tidak menerima format ribuan, koma desimal, huruf, simbol mata uang, atau spasi.
    text = raw.strip()
    if ',' in text or ' ' in text or any(ch.isalpha() for ch in text):
        errors[field_key] = f'{field_label} harus diisi angka saja. Gunakan titik untuk desimal, contoh: 1825.00 atau 1.45.'
        return default
    if text.count('.') > 1:
        errors[field_key] = f'{field_label} tidak valid. Hanya boleh memakai satu titik desimal, contoh: 1825.00.'
        return default
    if not text.replace('.', '', 1).isdigit():
        errors[field_key] = f'{field_label} harus berupa angka saja, tanpa huruf atau simbol. Contoh benar: 1825.00.'
        return default

    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        errors[field_key] = f'{field_label} harus berupa angka desimal valid. Contoh benar: 1825.00.'
        return default
    if number < min_value:
        errors[field_key] = f'{field_label} tidak boleh kurang dari {min_value}.'
        return default
    return number


def _clean_int_id(value, field_key, field_label, errors, *, default=0, min_value=0):
    """Validasi ketat bilangan bulat HTML: 177500."""
    raw = (value or '').strip()
    if raw == '':
        return default
    text = raw.strip()
    if not text.isdigit():
        errors[field_key] = f'{field_label} harus berupa angka bulat saja. Contoh benar: 177500. Jangan gunakan titik, koma, huruf, atau simbol.'
        return default
    try:
        number = int(text)
    except (TypeError, ValueError):
        errors[field_key] = f'{field_label} harus berupa bilangan bulat valid. Contoh benar: 177500.'
        return default
    if number < min_value:
        errors[field_key] = f'{field_label} tidak boleh kurang dari {min_value}.'
        return default
    return number


def _pond_context(request, pond=None, errors=None, mode='add'):
    return {
        'pond': pond,
        'mode': mode,
        'form_data': request.POST if request.method == 'POST' else None,
        'form_errors': errors or {},
        'status_choices': Pond.STATUS,
    }


def _apply_pond_form(request, pond=None):
    errors = {}
    code = (request.POST.get('code') or '').strip().upper()
    name = (request.POST.get('name') or '').strip()

    if not code:
        errors['code'] = 'Kode Kolam wajib diisi, contoh: K-01.'
    if not name:
        errors['name'] = 'Nama Kolam wajib diisi, contoh: Kolam 1.'

    duplicate = Pond.objects.filter(code=code)
    if pond and pond.pk:
        duplicate = duplicate.exclude(pk=pond.pk)
    if code and duplicate.exists():
        errors['code'] = f'Kode Kolam {code} sudah dipakai. Gunakan kode lain.'

    area_m2 = _clean_decimal_id(request.POST.get('area_m2'), 'area_m2', 'Luas Kolam', errors)
    depth_m = _clean_decimal_id(request.POST.get('depth_m'), 'depth_m', 'Kedalaman', errors)
    capacity_seed = _clean_int_id(request.POST.get('capacity_seed'), 'capacity_seed', 'Kapasitas Tebar', errors)

    status = request.POST.get('status') or 'Persiapan'
    valid_status = [choice[0] for choice in Pond.STATUS]
    if status not in valid_status:
        errors['status'] = 'Status kolam tidak valid.'

    if errors:
        return None, errors

    if pond is None:
        pond = Pond()
    pond.code = code
    pond.name = name
    pond.area_m2 = area_m2
    pond.depth_m = depth_m
    pond.capacity_seed = capacity_seed
    pond.pond_type = (request.POST.get('pond_type') or '').strip()
    pond.status = status
    pond.location = (request.POST.get('location') or '').strip()
    pond.notes = (request.POST.get('notes') or '').strip()
    if request.FILES.get('photo'):
        pond.photo = request.FILES.get('photo')
    pond.save()
    return pond, {}


@login_required
@permission_required('ponds.view')
def list_ponds(request):
    ponds = Pond.objects.all().order_by('code')
    page_obj = paginate_queryset(request, ponds, per_page=9)
    return render(request, 'ponds/list.html', {'ponds': page_obj, 'page_obj': page_obj})


@login_required
@permission_required('ponds.view')
def add_pond(request):
    if request.method == 'POST':
        pond, errors = _apply_pond_form(request)
        if not errors:
            messages.success(request, 'Data kolam berhasil disimpan.')
            return redirect('ponds:list')
        messages.error(request, 'Data belum bisa disimpan. Periksa kembali format nilai yang ditandai.')
        return render(request, 'ponds/form.html', _pond_context(request, errors=errors))
    return render(request, 'ponds/form.html', _pond_context(request))


@login_required
@permission_required('ponds.view')
def detail_pond(request, pk):
    return render(request, 'ponds/detail.html', {'pond': get_object_or_404(Pond, pk=pk)})


@login_required
@permission_required('ponds.view')
def edit_pond(request, pk):
    pond = get_object_or_404(Pond, pk=pk)
    if request.method == 'POST':
        updated, errors = _apply_pond_form(request, pond=pond)
        if not errors:
            messages.success(request, 'Data kolam berhasil diperbarui.')
            return redirect('ponds:list')
        messages.error(request, 'Perubahan belum disimpan. Periksa kembali format nilai yang ditandai.')
        return render(request, 'ponds/form.html', _pond_context(request, pond=pond, errors=errors, mode='edit'))
    return render(request, 'ponds/form.html', _pond_context(request, pond=pond, mode='edit'))


@login_required
@permission_required('ponds.view')
@require_POST
def delete_pond(request, pk):
    get_object_or_404(Pond, pk=pk).delete()
    messages.success(request, 'Data kolam berhasil dihapus.')
    return redirect('ponds:list')
