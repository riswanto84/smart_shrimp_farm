# Perbaikan Estimasi Kolam Selesai Panen

Pembaruan ini memastikan kolam berstatus **Panen** atau memiliki panen bertipe **Total/Final/Selesai** setelah sampling terakhir tidak ikut dalam biomassa aktif dan proyeksi DOC 120.

## Logika baru

- Panen total/final: biomassa aktif menjadi nol dan dikeluarkan dari proyeksi.
- Panen parsial: berat panen dikurangi dari biomassa sampling terbaru.
- Populasi setelah panen parsial dikurangi berdasarkan size panen; bila size tidak tersedia, digunakan pengurangan proporsional biomassa.
- Biomassa aktif memakai sampling terbaru masing-masing kolam, tidak lagi mewajibkan semua kolam memiliki tanggal sampling yang sama.
- Dashboard memisahkan Panen Riil, Estimasi Produksi Aktif, dan Total Potensi Siklus.
- Tidak memerlukan migrasi database.
