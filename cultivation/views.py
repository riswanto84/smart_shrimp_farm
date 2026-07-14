from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.rbac import owner_required, is_owner
from core.reporting import export_pdf, angka

from .forms import CultivationCycleForm
from .models import CultivationCycle
from .services import build_cycle_final_snapshot


@login_required
def cycle_list(request):
    return render(
        request,
        "cultivation/cycle_list.html",
        {
            "cycles": CultivationCycle.objects.all(),
            "can_manage_cycles": is_owner(request.user),
        },
    )


@owner_required
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
def cycle_report_pdf(request, pk):
    """Laporan akhir siklus selesai; dapat dicetak oleh semua role yang login."""
    cycle = get_object_or_404(CultivationCycle, pk=pk)
    if cycle.status != CultivationCycle.STATUS_COMPLETED:
        messages.warning(request, "Laporan akhir hanya tersedia untuk siklus yang sudah selesai.")
        return redirect("cultivation:list")

    snapshot = cycle.final_snapshot or build_cycle_final_snapshot(cycle)

    from operations.models import SamplingRecord, Harvest, SiphonRecord, AncoCheck, DailyParameter

    samples = SamplingRecord.objects.filter(cycle=cycle).select_related("pond")
    latest_date = samples.order_by("-date", "-id").values_list("date", flat=True).first()
    latest_rows = []
    if latest_date:
        seen = set()
        for item in samples.filter(date=latest_date).order_by("pond__name", "-id"):
            if item.pond_id in seen:
                continue
            seen.add(item.pond_id)
            latest_rows.append([
                item.pond.name,
                item.doc,
                angka(item.abw_g, 2),
                angka(item.size, 2),
                angka(item.adg_weekly, 3),
                angka(item.estimated_sr, 2),
                angka(item.biomass_kg, 2),
                angka(item.fcr, 2),
                angka(item.cumulative_feed_kg, 2),
            ])

    headers = ["Indikator", "Nilai", "Keterangan"]
    rows = [
        ["Nama Siklus", cycle.name, cycle.get_status_display()],
        ["Periode", f"{cycle.start_date.strftime('%d/%m/%Y')} s.d. {(cycle.actual_end_date or cycle.target_end_date).strftime('%d/%m/%Y')}", f"Durasi target {cycle.target_duration_days} hari"],
        ["Tanggal Selesai Aktual", cycle.actual_end_date.strftime('%d/%m/%Y') if cycle.actual_end_date else "-", "Arsip siklus"],
        ["Jumlah Kolam Sampling Terakhir", snapshot.get("pond_count", 0), f"Sampling {latest_date.strftime('%d/%m/%Y') if latest_date else '-'}"],
        ["Rata-rata ABW", f"{angka(snapshot.get('average_abw_g', 0), 2)} g", "Sampling terakhir"],
        ["Rata-rata ADG", f"{angka(snapshot.get('average_adg', 0), 3)} g/hari", "Sampling terakhir"],
        ["Rata-rata FCR", angka(snapshot.get("average_fcr", 0), 2), "Sampling terakhir"],
        ["Biomassa FR Akhir", f"{angka(snapshot.get('biomass_fr_kg', 0), 2)} kg", "Sampling terakhir"],
        ["Total Panen Tercatat", f"{angka(snapshot.get('harvest_total_kg', 0), 2)} kg", f"{Harvest.objects.filter(cycle=cycle).count()} transaksi panen"],
        ["Total Pakan Tercatat", f"{angka(snapshot.get('feed_total_kg', 0), 2)} kg", "Selama siklus"],
        ["Total Mortalitas Siphon", f"{angka(snapshot.get('mortality_total', 0), 0)} ekor", f"{SiphonRecord.objects.filter(cycle=cycle).count()} pencatatan"],
        ["Jumlah Cek Anco", AncoCheck.objects.filter(cycle=cycle).count(), "Selama siklus"],
        ["Jumlah Parameter Harian", DailyParameter.objects.filter(cycle=cycle).count(), "Selama siklus"],
    ]

    if latest_rows:
        rows.append(["Rincian sampling terakhir", "Lihat tabel lanjutan", "Per kolam"])
        rows.extend([
            [f"{r[0]} · DOC {r[1]}", f"ABW {r[2]} g · Size {r[3]} · FCR {r[7]}", f"ADG {r[4]} · SR {r[5]}% · Biomassa {r[6]} kg · Pakan {r[8]} kg"]
            for r in latest_rows
        ])

    notes = (cycle.notes or "-").strip()
    rows.append(["Catatan Siklus", notes, "Dokumen arsip final"])

    return export_pdf(
        filename=f"laporan_akhir_{cycle.name.lower().replace(' ', '_')}",
        title=f"Laporan Akhir {cycle.name}",
        subtitle="Ringkasan kinerja budidaya pada siklus yang telah selesai",
        headers=headers,
        rows=rows,
    )


@owner_required
@require_POST
def select_cycle(request):
    cycle = get_object_or_404(CultivationCycle, pk=request.POST.get("cycle"))
    request.session["selected_cycle_id"] = cycle.pk
    messages.success(request, f"Siklus aktif tampilan: {cycle.name}.")
    return redirect(request.META.get("HTTP_REFERER") or "core:dashboard")
