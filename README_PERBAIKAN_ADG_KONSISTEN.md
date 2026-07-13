# Perbaikan konsistensi Rata-rata ADG

Perubahan:
- Kartu Rata-rata ADG memakai kolom `adg_weekly`/ADG Weekly Actual.
- Satu data terbaru per kolam dipilih berdasarkan tanggal terbaru.
- Jika ada duplikat kolam+tanggal, record dengan PK terkecil menjadi record kanonik, sama dengan urutan tabel.
- Import ulang memperbarui record kanonik dan menghapus duplikat lama.
- Tabel sampling diurutkan deterministik berdasarkan tanggal terbaru lalu PK terkecil.

Hasil yang diharapkan untuk data 12/07/2026:
(0,29 + 0,25 + 0,30 + 0,23 + 0,26 + 0,17) / 6 = 0,25 gr/hari.

Setelah pemasangan, lakukan import ulang dengan opsi Perbarui data lama agar duplikat lama dibersihkan.
