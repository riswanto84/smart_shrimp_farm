from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CultivationCycleForm
from .models import CultivationCycle


@login_required
def cycle_list(request):
    return render(
        request,
        "cultivation/cycle_list.html",
        {"cycles": CultivationCycle.objects.all()},
    )


@login_required
def cycle_form(request, pk=None):
    obj = get_object_or_404(CultivationCycle, pk=pk) if pk else None

    if request.method == "POST":
        form = CultivationCycleForm(request.POST, instance=obj)
        if form.is_valid():
            cycle = form.save()
            request.session["selected_cycle_id"] = cycle.pk
            messages.success(request, "Siklus budidaya berhasil disimpan.")
            return redirect("cultivation:list")
        messages.error(request, "Data siklus belum valid. Periksa kembali kolom yang ditandai.")
    else:
        form = CultivationCycleForm(instance=obj)

    return render(
        request,
        "cultivation/cycle_form.html",
        {
            "obj": obj,
            "form": form,
            "statuses": CultivationCycle.STATUS_CHOICES,
        },
    )


@login_required
@require_POST
def select_cycle(request):
    cycle = get_object_or_404(CultivationCycle, pk=request.POST.get("cycle"))
    request.session["selected_cycle_id"] = cycle.pk
    messages.success(request, f"Siklus aktif tampilan: {cycle.name}.")
    return redirect(request.META.get("HTTP_REFERER") or "core:dashboard")
