# Perbaikan Neraca – Biomassa Indeks Udang Tersisa

Perubahan:

- Neraca otomatis menghitung biomassa indeks terakhir per kolam pada siklus aktif/panen.
- Panen yang terjadi setelah sampling terakhir dikurangkan dari biomassa indeks.
- Jika terdapat panen total setelah sampling, sisa biomassa kolam menjadi nol.
- Nilai biomassa = sisa biomassa indeks × rata-rata tertimbang harga penjualan per kg.
- Prioritas harga: penjualan siklus aktif → seluruh penjualan → harga estimasi siklus aktif.
- Nilai ditampilkan sebagai **Aset – Biomassa Udang Tersisa (Indeks)** pada halaman dan PDF neraca.
- Nilai biomassa akhir juga menjadi penyesuaian laba berjalan karena biaya budidaya telah dibebankan sebagai pengeluaran.
- Halaman neraca menampilkan rincian per siklus dan kolam untuk audit.

Tidak ada migrasi database baru.
