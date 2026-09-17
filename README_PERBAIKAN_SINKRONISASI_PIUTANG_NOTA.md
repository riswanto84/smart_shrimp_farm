# Perbaikan Sinkronisasi Nota Penjualan dan Piutang Usaha

## Perubahan
- Nota berstatus **Belum Lunas** atau **Menunggu Pembayaran** otomatis membuat kartu Piutang Usaha.
- Nilai awal mengikuti total nota.
- Pembayaran awal mengikuti Cash/Transfer/QRIS/Metode lainnya yang telah dicatat pada nota.
- Pembayaran campuran dihitung dari jumlah seluruh komponennya.
- Saat nota diedit, nomor nota, pelanggan, nilai awal, pembayaran, dan saldo piutang ikut diperbarui.
- Saat nota menjadi **Lunas**, kartu piutang otomatis ditutup.
- Nota Gagal, Expired, Dibatalkan, atau Refund tidak menjadi piutang aktif.
- Halaman Piutang Usaha melakukan backfill otomatis untuk nota lama yang masih terbuka.
- Disediakan command manual: `python manage.py sync_sales_receivables`.

## Rumus
`Sisa Saldo = Total Nota - Pembayaran yang sudah dicatat`

## Instalasi
Tidak memerlukan migrasi database.

```bash
source env/bin/activate
python manage.py check
python manage.py sync_sales_receivables
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
