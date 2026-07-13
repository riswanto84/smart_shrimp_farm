# Perbaikan Dashboard Utama — Data Aktual

Perubahan:

1. Grafik **Biomassa Produksi (Ton)** tidak lagi memakai angka hardcode 24,8 ton.
2. Data produksi diambil dari `SamplingRecord.biomass_kg` pada satu tanggal sampling terbaru dalam siklus aktif.
3. Jika ada duplikat kolam pada tanggal yang sama, hanya record terbaru per kolam yang digunakan.
4. Total produksi adalah penjumlahan Biomassa FR sampling terbaru dan dikonversi dari kg ke ton.
5. Kartu parameter air tidak lagi memakai nilai fallback/dummy.
6. Jika suhu, pH, DO, salinitas, atau kecerahan belum diinput, dashboard menampilkan tanda `—` dan `Belum ada data`.
7. Amonia menampilkan `Belum tersedia` karena model `DailyParameter` belum memiliki field amonia.
8. Grafik suhu menggunakan maksimal 7 pencatatan suhu aktual terakhir pada kolam dari parameter terbaru. Jika tidak ada input suhu, grafik menampilkan keadaan kosong.
9. Aktivitas contoh dihapus agar dashboard tidak menampilkan kegiatan fiktif.

Tidak ada perubahan model atau migrasi database.
