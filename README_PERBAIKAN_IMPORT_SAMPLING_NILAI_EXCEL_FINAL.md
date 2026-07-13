# Perbaikan Import Sampling — Nilai Excel Dipertahankan

Perbaikan ini memastikan angka final pada laporan Excel sampling lebar disimpan apa adanya dan tidak ditimpa kalkulasi otomatis model.

Kolom yang dipertahankan saat import:
- ABW Last, Today, dan Target
- Size
- ADG Weekly Target dan Actual
- ADG Accum
- SR FR dan SR Index
- Biomassa FR dan Biomassa Index
- FCR
- Populasi FR dan Populasi Index
- Pakan Kumulatif, Tebar, F/D, FR, dan Index

Contoh K2 tanggal 12/07/2026: ADG Weekly Actual tetap 0,25; tidak dihitung ulang menjadi 8,75 - 7,03 = 1,72.

Input sampling manual tetap menggunakan kalkulasi otomatis aplikasi. Setelah memasang versi ini, impor ulang laporan Excel dengan mode "Perbarui data lama".
