# Perbaikan Kasir Penjualan

Perubahan:
- Pembayaran Campuran: Cash, Transfer, QRIS, dan metode lain.
- Metode Lainnya dengan nama metode kustom.
- Status Lunas/Belum Lunas dihitung otomatis dari total pembayaran.
- Upload multi-file bukti transfer/tanda terima dan dokumen penjualan.
- Maksimal 10 MB per file; PDF, gambar, Word, dan Excel.
- Daftar serta hapus lampiran pada halaman edit nota.
- Layout nota HTML dan PDF diubah menjadi vertikal agar Qty, Harga/Kg, dan Subtotal tidak bertumpuk.
- Lebar cetak HTML menjadi 90 mm; PDF tetap thermal 80 mm dengan tata letak aman.

## Instalasi VPS
```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py migrate sales
python manage.py check
sudo systemctl restart smartshrimp.service
sudo systemctl reload nginx
```

Pastikan `[X] 0007_sale_mixed_payment_documents` muncul pada `python manage.py showmigrations sales`.
