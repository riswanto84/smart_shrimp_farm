# Pencarian Global Semua Tabel Data

Fitur:
- Search bar otomatis pada seluruh tabel data di aplikasi.
- Pencarian real-time dengan debounce.
- Tidak peka huruf besar/kecil dan aksen.
- Tombol hapus pencarian.
- Jumlah hasil yang terlihat.
- Pesan ketika tidak ditemukan data.
- Tampilan responsif untuk desktop dan mobile.
- Tidak mengubah model, database, atau migration.

Catatan:
- Pencarian bekerja pada data yang sedang ditampilkan pada halaman aktif.
- Pagination dan filter server yang sudah ada tetap berfungsi.
- Untuk menonaktifkan pencarian pada tabel tertentu, tambahkan:
  data-global-search="off"
  pada elemen <table>.
