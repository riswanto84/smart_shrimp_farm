# Kasir Multiukuran

Perubahan:
- Satu pelanggan dapat membeli beberapa ukuran udang dalam satu nota.
- Tombol Tambah Ukuran Udang untuk menambah baris item.
- Setiap item memiliki sumber panen, size, berat, harga/kg, dan subtotal.
- Total berat serta total transaksi dihitung otomatis.
- Edit nota dapat menambah, mengubah, dan menghapus item.
- Nota HTML dan PDF memakai SaleItem yang sudah tersedia.
- Penyimpanan memakai transaction.atomic.
- Tidak ada perubahan model atau migration.
- Tidak perlu makemigrations atau migrate.
