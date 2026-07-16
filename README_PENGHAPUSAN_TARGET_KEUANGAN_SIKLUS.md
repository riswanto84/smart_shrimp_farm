# Perbaikan Form Siklus Budidaya

Field berikut dihapus dari tampilan dan proses penyimpanan form Siklus Budidaya:

- Harga Jual Estimasi
- Target Biaya Produksi

Dashboard Produksi juga tidak lagi menampilkan target omzet, target biaya, atau target laba yang berasal dari Siklus.

Kolom database lama tetap dipertahankan agar kompatibel dengan data dan migration sebelumnya. Karena itu tidak diperlukan `makemigrations` atau `migrate`. Data transaksi dan analisis keuangan tetap dikelola melalui modul Penjualan dan Keuangan.
