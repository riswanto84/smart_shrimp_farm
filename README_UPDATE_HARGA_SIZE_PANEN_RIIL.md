# Update Dashboard Harga dan Size Panen Riil

Dashboard utama sekarang menampilkan:

- Size panen riil terbaru.
- Harga panen terbaru per kilogram.
- Harga jual rata-rata tertimbang pada setiap record panen.
- Berat panen, berat terjual, harga/kg, dan nilai penjualan pada riwayat panen.
- Pencocokan otomatis melalui `SaleItem.harvest`.

Tidak ada perubahan model dan tidak memerlukan migrasi database. Harga hanya tampil jika item penjualan terhubung ke data panen.
