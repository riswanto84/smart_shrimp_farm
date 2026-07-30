# Likuiditas Akuntansi dan Operasional Tambak

Perubahan terbatas pada laporan neraca:

- Memisahkan **Likuiditas Akuntansi** dan **Likuiditas Operasional Tambak**.
- Menambahkan Current Ratio Operasional, Coverage Biomassa, Nilai Biomassa Aktif, dan Modal Kerja Operasional.
- Biomassa memakai `biomass_index_kg` dari sampling terakhir pada kolam/siklus aktif atau panen.
- Panen setelah sampling dikurangkan; panen total/final membuat sisa biomassa nol.
- Harga memakai rata-rata tertimbang item penjualan hingga tanggal laporan, dengan fallback harga estimasi siklus.
- Nilai biomassa tidak dimasukkan ke total aset neraca akuntansi dan diberi catatan bahwa biomassa bukan kas siap pakai.
- Tidak memerlukan migrasi database.
