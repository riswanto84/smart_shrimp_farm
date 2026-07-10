# Perbaikan Status Ollama & Siklus Budidaya

## Siklus Budidaya
- Menu baru: **Siklus Budidaya** (`/cycles/`).
- Durasi default: **135 hari**, termasuk persiapan kolam.
- Target tanggal selesai dihitung otomatis dari tanggal mulai.
- Status: Persiapan, Aktif, Panen, Selesai.
- DOC tetap diinput manual pada form operasional.
- Pemilih siklus tersedia pada topbar dan disimpan dalam session pengguna.
- Data baru Parameter Harian, Data Harian, Cek Anco, Sampling, Siphon, Panen, Pengeluaran, Penjualan, serta Chat AI otomatis dikaitkan dengan siklus terpilih.
- Dashboard, laporan keuangan, penjualan, investor, dan daftar operasional utama difilter menurut siklus terpilih.

## Status Ollama
- Status dashboard diperiksa langsung melalui API Ollama `/api/tags`.
- Kondisi Online, Offline, Timeout, dan Model Belum Tersedia ditampilkan sesuai hasil koneksi nyata.
- Tombol Cek Ulang dan pemeriksaan otomatis setiap 30 detik.

## Instalasi
```bash
python3 manage.py check
python3 manage.py migrate
python3 manage.py collectstatic --noinput
```

Setelah migrasi, buat siklus pertama melalui menu **Siklus Budidaya**, misalnya `Siklus 2026-01`.
