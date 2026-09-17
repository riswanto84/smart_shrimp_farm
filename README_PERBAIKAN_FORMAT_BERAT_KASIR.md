# Perbaikan Format Berat Kasir Penjualan

Input **Berat (Kg)** pada Kasir Penjualan dan Edit Nota sekarang menerima format angka Indonesia maupun internasional:

- `1188,40`
- `1.188,40`
- `1188.40`
- `1,188.40`

Saat field kehilangan fokus, angka otomatis ditampilkan dalam format Indonesia, misalnya `1.188,4`. Saat form disimpan, nilai dinormalisasi menjadi format desimal standar agar Django menyimpan `1188.40` secara benar.

Perbaikan dilakukan di sisi browser dan server. Tidak memerlukan migrasi database.
