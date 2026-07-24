# Perbaikan Konsistensi Laba Rugi dan Neraca

Perbaikan pada versi ini:

1. Periode default laporan tahun berjalan berakhir pada tanggal hari ini, bukan 31 Desember.
2. Tanggal masa depan tidak lagi menyebabkan penyusutan masa depan diakui.
3. Laporan Laba Rugi Pajak dan Neraca memakai satu fungsi perhitungan laba/rugi yang sama.
4. Pendapatan, beban operasional, dan penyusutan tahun berjalan pada Neraca kini sama sumbernya dengan Laporan Laba Rugi.
5. Status Neraca dibedakan menjadi:
   - Seimbang dan Terekonsiliasi;
   - Seimbang dengan Catatan;
   - Belum Seimbang.
6. Neraca tidak lagi menampilkan status hijau "Seimbang" tanpa catatan ketika akun saldo awal/modal belum direkonsiliasi.

## Pemeriksaan setelah pemasangan

Buka Laba Rugi dengan periode 1 Januari sampai tanggal posisi Neraca. Nilai Laba/Rugi Bersih harus sama persis dengan Laba/Rugi Tahun Berjalan pada Neraca.
