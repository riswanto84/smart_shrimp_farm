# Perubahan Akses Siklus Budidaya

Fitur Siklus Budidaya sekarang hanya dapat diakses oleh:

- Superuser Django
- Role `Owner`
- Role `Owner Tambak`

Perubahan mencakup:

- Menu Siklus Budidaya hanya tampil untuk Owner.
- Pemilih siklus di topbar hanya tampil untuk Owner.
- URL daftar, tambah, edit, dan pilih siklus dilindungi di backend.
- Role lain yang membuka URL langsung menerima halaman 403.

Data siklus terpilih tetap tersedia di sistem sebagai konteks agar transaksi operasional dapat tetap dikaitkan dengan siklus aktif.
