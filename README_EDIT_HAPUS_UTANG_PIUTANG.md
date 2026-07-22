# Penambahan Tombol Edit dan Hapus Utang/Piutang

Perubahan:
- Tombol Lihat, Edit, dan Hapus tersedia langsung pada kolom Aksi di daftar Utang Usaha dan Piutang Usaha.
- Tombol menggunakan ikon agar konsisten dengan modul lain.
- Penghapusan hanya dapat dilakukan melalui request POST dan dilindungi CSRF.
- Sebelum penghapusan, pengguna mendapat konfirmasi bahwa pembayaran dan dokumen terkait ikut terhapus.
- Tombol Edit membuka form yang sama dengan data transaksi terisi otomatis.
- Fitur upload multidokumen tetap dipertahankan.

Penerapan di VPS:
1. Backup aplikasi dan database.
2. Salin file aplikasi terbaru ke folder produksi tanpa menimpa database produksi.
3. Jalankan `python manage.py migrate finance`.
4. Jalankan `python manage.py check`.
5. Restart service `smartshrimp.service` dan reload Nginx.
