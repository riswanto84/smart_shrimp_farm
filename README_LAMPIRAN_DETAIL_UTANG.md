# Lampiran pada Detail Utang/Piutang

Perbaikan ini menampilkan seluruh file yang sudah diunggah pada halaman detail Utang/Piutang Usaha, termasuk dokumen transaksi dan bukti pembayaran.

## Fitur
- Galeri seluruh lampiran dengan jumlah file.
- Preview gambar langsung pada kartu.
- Tombol Lihat, Unduh, dan Hapus.
- Preview PDF/gambar di tab baru melalui endpoint Django yang terlindungi login.
- Dokumen pembayaran ditandai tanggal pembayarannya.
- Lampiran tetap terlihat pada halaman Edit.
- Riwayat pembayaran menampilkan lampiran bukti pembayaran.

## Deployment
```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Tidak ada migration database baru.
