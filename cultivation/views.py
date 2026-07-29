from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta

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
        ["Target Produksi", f"{angka(cycle.target_biomass_ton, 2)} ton", f"DOC {cycle.target_doc} · Size {angka(cycle.target_size, 0)}"],
        ["Target Kinerja", f"FCR {angka(cycle.target_fcr, 2)} · SR {angka(cycle.target_sr_percent, 1)}%", f"ADG {angka(cycle.target_adg, 3)} g/hari"],
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
@transaction.atomic
def close_and_create_next_cycle(request, pk):
    """Tutup siklus lama sebagai arsip dan buat siklus berikutnya yang kosong.

    Data lama tidak dihapus atau diubah kepemilikannya. Seluruh nilai operasional
    pada siklus baru otomatis nol karena setiap transaksi tetap terikat pada
    ``cycle`` asalnya dan tampilan aplikasi difilter menggunakan siklus terpilih.
    """
    cycle = get_object_or_404(CultivationCycle.objects.select_for_update(), pk=pk)
    if cycle.status == CultivationCycle.STATUS_COMPLETED:
        messages.warning(request, "Siklus tersebut sudah selesai dan telah menjadi arsip.")
        return redirect("cultivation:list")

    # Jangan menutup siklus bila masih ada siklus lain yang terbuka. Ini menjaga
    # agar transaksi baru tidak salah masuk ke dua siklus aktif sekaligus.
    other_open = CultivationCycle.objects.exclude(pk=cycle.pk).filter(
        status__in=[
            CultivationCycle.STATUS_PREPARATION,
            CultivationCycle.STATUS_ACTIVE,
            CultivationCycle.STATUS_HARVEST,
        ]
    ).first()
    if other_open:
        messages.error(
            request,
            f"Masih ada siklus terbuka: {other_open.name}. Selesaikan atau tutup siklus tersebut terlebih dahulu.",
        )
        return redirect("cultivation:list")

    end_date_raw = (request.POST.get("actual_end_date") or "").strip()
    if end_date_raw:
        try:
            actual_end_date = CultivationCycle._coerce_date(end_date_raw)
        except (TypeError, ValueError):
            messages.error(request, "Tanggal selesai aktual tidak valid.")
            return redirect("cultivation:list")
    else:
        actual_end_date = timezone.localdate()

    if actual_end_date < cycle.start_date:
        messages.error(request, "Tanggal selesai tidak boleh lebih awal dari tanggal mulai siklus.")
        return redirect("cultivation:list")

    cycle.status = CultivationCycle.STATUS_COMPLETED
    cycle.actual_end_date = actual_end_date
    cycle.save(update_fields=["status", "actual_end_date", "completed_at", "updated_at"])

    requested_name = (request.POST.get("next_cycle_name") or "").strip()
    if not requested_name:
        base = "Siklus"
        number = CultivationCycle.objects.count() + 1
        requested_name = f"{base} {number}"
        while CultivationCycle.objects.filter(name=requested_name).exists():
            number += 1
            requested_name = f"{base} {number}"
    elif CultivationCycle.objects.filter(name=requested_name).exists():
        messages.error(request, "Nama siklus berikutnya sudah digunakan.")
        transaction.set_rollback(True)
        return redirect("cultivation:list")

    next_start_raw = (request.POST.get("next_start_date") or "").strip()
    if next_start_raw:
        try:
            next_start_date = CultivationCycle._coerce_date(next_start_raw)
        except (TypeError, ValueError):
            messages.error(request, "Tanggal mulai siklus berikutnya tidak valid.")
            transaction.set_rollback(True)
            return redirect("cultivation:list")
    else:
        next_start_date = actual_end_date + timedelta(days=1)

    if next_start_date <= actual_end_date:
        messages.error(request, "Tanggal mulai siklus berikutnya harus setelah tanggal selesai siklus lama.")
        transaction.set_rollback(True)
        return redirect("cultivation:list")

    next_cycle = CultivationCycle.objects.create(
        name=requested_name,
        start_date=next_start_date,
        target_duration_days=cycle.target_duration_days,
        target_doc=cycle.target_doc,
        target_size=cycle.target_size,
        target_biomass_ton=cycle.target_biomass_ton,
        target_sr_percent=cycle.target_sr_percent,
        target_fcr=cycle.target_fcr,
        target_adg=cycle.target_adg,
        target_population=0,
        estimated_price_per_kg=cycle.estimated_price_per_kg,
        target_cost=cycle.target_cost,
        status=CultivationCycle.STATUS_PREPARATION,
        notes="",
    )
    request.session["selected_cycle_id"] = next_cycle.pk
    request.session.modified = True
    messages.success(
        request,
        f"{cycle.name} berhasil ditutup dan diarsipkan. {next_cycle.name} telah dibuat dengan nilai operasional awal nol.",
    )
    return redirect("core:dashboard")


@owner_required
@require_POST
def select_cycle(request):
    cycle = get_object_or_404(CultivationCycle, pk=request.POST.get("cycle"))
    request.session["selected_cycle_id"] = cycle.pk
    messages.success(request, f"Siklus aktif tampilan: {cycle.name}.")
    return redirect(request.META.get("HTTP_REFERER") or "core:dashboard")
