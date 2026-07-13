# Perbaikan ADG Weekly Actual

- Import sampling format laporan lebar kini membaca kolom `ADG Weekly (Gr/Day) -> Actual`.
- Nilai Actual dari Excel dipertahankan saat `save()` dan tidak ditimpa perhitungan otomatis model.
- Kartu Rata-rata ADG tetap menghitung rata-rata `adg_weekly` dari satu sampling terakhir setiap kolam.
- Jika file template ringkas tidak memiliki kolom Actual, aplikasi tetap memakai perhitungan otomatis seperti sebelumnya.

Setelah instalasi, impor ulang file laporan sampling dengan mode **Perbarui data lama** agar nilai lama yang terlanjur salah diperbarui.
