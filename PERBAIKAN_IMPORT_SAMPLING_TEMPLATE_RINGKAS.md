# Perbaikan Import Data Sampling

Perbaikan ini mengatasi kolom template sampling yang sebelumnya tidak masuk ke database karena parser masih membaca nomor kolom format lama.

Kolom yang sekarang dipetakan berdasarkan nama header:
- ADG Weekly Target
- Pakan Kumulatif (Kg)
- Tebar
- F/D Pakan Harian
- FR (%)
- Populasi Index
- Index
- Catatan

Parser sekarang mendukung template ringkas aplikasi dan format sampling lama/lebar, serta tidak bergantung pada posisi kolom tetap.
