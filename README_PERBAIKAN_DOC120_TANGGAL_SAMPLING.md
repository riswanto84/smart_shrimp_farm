# Perbaikan Estimasi DOC 120 dan Biomassa Tersisa

Perubahan ini mencegah panen parsial dan mortalitas pada tanggal yang sama dengan sampling terakhir dihitung dua kali.

## Logika baru

- Sampling terbaru menjadi snapshot populasi dan biomassa.
- Panen parsial hanya mengurangi snapshot jika `tanggal panen > tanggal sampling`.
- Mortalitas siphon hanya mengurangi snapshot jika `tanggal siphon > tanggal sampling`.
- Kolam panen total/selesai tetap dikeluarkan dari estimasi aktif.
- Proyeksi DOC 120 tetap dihitung dari populasi tersisa dan ABW proyeksi.

## Alasan

Database saat ini menyimpan tanggal tanpa urutan waktu yang cukup untuk memastikan apakah sampling dilakukan sebelum atau sesudah panen/siphon pada hari yang sama. Karena nilai sampling dianggap snapshot terbaru, transaksi pada tanggal yang sama tidak dikurangi kembali.

Tidak ada perubahan model atau migration.
