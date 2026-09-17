# Perbaikan Dashboard Produksi — Populasi Tebar dari Master Kolam

Perubahan ini membuat nilai **Data Tebar / Populasi Tebar** pada Dashboard Produksi
selalu dihitung dari jumlah `capacity_seed` seluruh data pada menu **Master Kolam**.

Sumber lama (Stocking atau fallback Sampling) tidak lagi dipakai untuk KPI populasi
tebar, sehingga angka dashboard konsisten dengan kartu Master Kolam.

Tidak ada perubahan struktur database dan tidak diperlukan migration baru.
