# Perbaikan kartu Rata-rata ADG

Kartu **Rata-rata ADG** pada menu Data Sampling sekarang:

1. mengambil satu sampling terbaru untuk setiap kolam berdasarkan tanggal dan ID terbaru;
2. menggunakan field `adg_weekly` yang mewakili kolom Excel **ADG Weekly (Gr/Day) - Actual**;
3. tidak menggunakan ADG Target, ADG Accum, atau seluruh histori sampling;
4. menampilkan satuan `gr/hari` sesuai judul kolom Excel;
5. tetap mengikuti filter tanggal, kolam, dan siklus aktif.

Contoh data Actual 0,29; 0,25; 0,30; 0,23; 0,26; 0,17 menghasilkan rata-rata 0,25 gr/hari.

Setelah pemasangan, impor ulang Excel dengan mode **Perbarui data lama** agar nilai Actual yang sebelumnya sempat dihitung ulang tersimpan sesuai Excel.
