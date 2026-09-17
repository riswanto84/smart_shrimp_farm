# Perbaikan Dashboard Biomassa Terbaru

Kartu **Biomassa FR** pada halaman **Data Sampling** sekarang menjumlahkan hanya
record sampling terbaru dari setiap kolam.

Sebelumnya kartu tersebut memakai `SUM(biomass_kg)` atas seluruh riwayat sampling,
sehingga angka terus terakumulasi dan tidak menggambarkan biomassa terkini.

Aturan baru:

1. Query tetap mengikuti filter tanggal, kolam, dan siklus budidaya aktif.
2. Untuk setiap kolam dipilih satu sampling paling baru berdasarkan tanggal.
3. Jika ada lebih dari satu sampling pada tanggal yang sama, record dengan ID
   paling besar dipakai.
4. Nilai kartu adalah total Biomassa FR terbaru seluruh kolam yang terpilih.

Perubahan tidak membutuhkan migrasi database.
