# Perbaikan Tampilan Parameter Harian

Perubahan:
- Menghapus kolom **Kode Pakan** dari tabel Parameter Harian.
- Menghapus nilai kode pakan pada setiap baris tabel.
- Menyesuaikan colspan tabel kosong dari 12 menjadi 11.
- Menghapus penyebutan kode pakan pada deskripsi halaman agar tampilan konsisten.

Catatan:
- Field `feed_code` pada model/database tidak dihapus.
- Import, data lama, dan fitur lain tetap aman.
- Tidak memerlukan migration database.
