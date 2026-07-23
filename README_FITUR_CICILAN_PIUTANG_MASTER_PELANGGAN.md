# Fitur Pembayaran Sebagian Piutang & Master Pelanggan

Pembaruan ini menyempurnakan modul Piutang Usaha untuk transaksi pelanggan yang belum melunasi seluruh nilai nota.

## Fitur
- Piutang manual wajib memilih pembeli dari tabel **Master Pelanggan** (`sales.Customer`).
- Piutang otomatis dari Nota Penjualan membawa relasi pelanggan yang sama.
- Pembayaran dapat dicatat berkali-kali sebagai cicilan/angsuran.
- Setiap pembayaran menyimpan tanggal, nominal, metode, nomor bukti, catatan, dan multidokumen.
- Saldo dihitung otomatis: nilai awal dikurangi seluruh riwayat pembayaran.
- Status otomatis: Belum Dibayar, Sebagian, atau Lunas.
- Nota sumber otomatis berubah menjadi Lunas ketika saldo nol dan kembali Belum Lunas apabila pembayaran dihapus.
- Daftar dan detail piutang menampilkan identitas dari Master Pelanggan.

## Instalasi
```bash
source env/bin/activate
python manage.py migrate
python manage.py sync_sales_receivables
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
