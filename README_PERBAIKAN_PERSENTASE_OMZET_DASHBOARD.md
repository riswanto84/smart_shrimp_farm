# Perbaikan Persentase Omzet Dashboard

Perubahan:

- Menghapus persentase omzet statis `12.5%` pada dashboard.
- Omzet Hari Ini dihitung berdasarkan tanggal lokal aplikasi (`Asia/Jakarta`).
- Pembanding menggunakan omzet satu hari sebelumnya.
- Transaksi berstatus Gagal, Expired, Dibatalkan, dan Refund tidak dihitung.
- Jika omzet kemarin lebih dari nol, persentase dihitung dengan rumus:
  `(omzet hari ini - omzet kemarin) / omzet kemarin × 100%`.
- Jika omzet kemarin nol tetapi hari ini ada omzet, dashboard menampilkan
  `Baru ada omzet hari ini`, karena persentase pertumbuhan dari nol tidak terdefinisi.
- Jika hari ini dan kemarin sama-sama nol, dashboard menampilkan
  `Belum ada omzet hari ini maupun kemarin`.
- Omzet pada kartu dashboard kini benar-benar omzet hari ini, bukan total seluruh siklus.

File utama yang diperbarui:

- `core/views.py`
- `templates/core/dashboard.html`

Penerapan di VPS:

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
sudo systemctl restart smartshrimp.service
sudo systemctl reload nginx
```

Tidak ada migrasi database baru.
