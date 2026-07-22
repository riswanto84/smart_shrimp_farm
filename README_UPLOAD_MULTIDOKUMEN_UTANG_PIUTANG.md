# Upload Multidokumen Utang dan Piutang

## Fitur yang ditambahkan
- Upload beberapa dokumen sekaligus saat membuat atau mengedit utang/piutang.
- Upload dokumen tambahan dari halaman detail transaksi.
- Upload beberapa bukti pembayaran saat mencatat pembayaran.
- Daftar lampiran dapat dibuka langsung dan dokumen transaksi dapat dihapus.
- Format yang didukung: PDF, JPG/JPEG, PNG, WEBP, DOC/DOCX, XLS/XLSX.
- Batas ukuran: 10 MB per file.
- Penyimpanan: `media/finance/trade_documents/<tahun>/<bulan>/`.

## Instalasi di server
```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py migrate finance
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Pastikan konfigurasi `MEDIA_ROOT`, `MEDIA_URL`, dan Nginx untuk folder media sudah aktif.
