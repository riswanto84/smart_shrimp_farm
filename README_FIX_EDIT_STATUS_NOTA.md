# Perbaikan Edit Status Nota

Perubahan:
- Pilihan status pada halaman Edit Nota menjadi otoritatif.
- Memilih `Belum Lunas` tidak lagi dibalik otomatis menjadi `Lunas`.
- Jika nota penuh dibayar lalu diubah menjadi `Belum Lunas`, rincian pembayaran
  otomatis dikosongkan agar saldo piutang kembali terbuka.
- Jika diubah menjadi `Lunas`, pembayaran disesuaikan hingga total nota.
- `sync_sale_receivable()` tidak lagi menimpa `Sale.status`.
- Kartu Piutang Usaha mengikuti status dan rincian pembayaran pada nota.
- Tidak ada perubahan model, database, atau migration.
