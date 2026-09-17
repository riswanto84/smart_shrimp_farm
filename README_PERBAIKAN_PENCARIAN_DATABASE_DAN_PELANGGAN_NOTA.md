# Perbaikan pencarian database dan pelanggan nota

1. Pencarian tabel global sekarang mengirim parameter `q` ke server dan mencari pada QuerySet sebelum pagination. Dengan demikian, data pada halaman lain tetap dapat ditemukan.
2. Helper `core.search.apply_database_search` mencari field teks model serta field teks ForeignKey satu tingkat.
3. Field pelanggan pada Kasir/Edit Nota diganti menjadi autocomplete berbasis database, bukan select/dropdown biasa.
4. Autocomplete dapat mencari nama, nomor HP, email, dan alamat pelanggan.
5. Pengguna wajib memilih hasil pencarian agar ID pelanggan valid; field dapat dikosongkan untuk pelanggan umum.
6. Tidak ada perubahan model atau migration database.
