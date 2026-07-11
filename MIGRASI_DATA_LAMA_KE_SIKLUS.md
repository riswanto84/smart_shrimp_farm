# Migrasi Data Lama ke Siklus Budidaya

Perbaikan ini memastikan data lama tidak tampak hilang setelah fitur Siklus Budidaya diaktifkan.

## Perilaku baru

- Data lama dengan `cycle = NULL` tetap ditampilkan bersama siklus yang sedang dipilih.
- Migration otomatis mengaitkan data lama ke siklus aktif/terbuka terbaru jika siklus sudah tersedia.
- Data baru tetap otomatis masuk ke siklus yang dipilih.
- Berlaku untuk Parameter Harian, Cek Anco, Sampling, Siphon, Panen, data operasional lain, Pengeluaran Operasional, Penjualan, dan sesi Chat AI.

## Setelah deploy

```bash
python3 manage.py migrate
python3 manage.py backfill_cycle_data
```

Untuk memilih siklus tertentu:

```bash
python3 manage.py backfill_cycle_data --cycle-id 1
```

Command ini aman dijalankan berulang karena hanya memperbarui data dengan `cycle` yang masih kosong.
