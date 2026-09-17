# Perbaikan Catatan Invoice

Perubahan:
- Menghapus teks default "Pengiriman menggunakan mobil berpendingin".
- Invoice PDF/thermal hanya menampilkan `Sale.notes` dari database.
- Jika catatan transaksi kosong, bagian CATATAN tidak ditampilkan.
- Catatan mendukung beberapa baris.
- Tinggi nota thermal menyesuaikan panjang catatan agar tidak terpotong.
- Preview invoice HTML tetap memakai catatan transaksi dari database.
- Tidak ada perubahan model, database, atau migration.
