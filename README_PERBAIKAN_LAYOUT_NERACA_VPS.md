# Perbaikan Layout Laporan Neraca di VPS

Perbaikan ini mengisolasi seluruh class KPI dan grafik komposisi pada halaman Neraca agar tidak tertimpa class global dari `static/css/app.css` atau hasil `collectstatic` lama.

Perubahan utama:
- Class KPI diubah menjadi namespace `neraca-*`.
- Isi kartu KPI dipaksa tersusun vertikal dan tidak lagi mengikuti aturan flex global.
- Ukuran nilai KPI dibuat responsif dengan `clamp()`.
- Grid 4 kolom dipertahankan pada desktop dan berubah menjadi 2 kolom di bawah 1180px.
- Class progress bar komposisi aset juga diisolasi agar ukuran bar konsisten.
- Lebar halaman dan panel dibuat aman terhadap perbedaan sidebar, zoom, dan static cache di VPS.

Setelah deploy:

```bash
python manage.py collectstatic --clear --noinput
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Lakukan hard refresh browser dengan Command+Shift+R.
