# Dashboard Produksi – Grafik Perkembangan Biomassa

Perubahan utama:

- Grafik garis biomassa aktual dari seluruh batch Data Sampling pada siklus terpilih.
- Satu record terbaru per kolam per tanggal digunakan untuk mencegah duplikasi impor.
- Garis prediksi hingga DOC 120 dihitung dari ABW, ADG Actual, dan populasi terbaru.
- Garis target panen 25 ton.
- Tooltip menampilkan ABW, ADG, FCR, SR, dan populasi pada setiap titik aktual.
- KPI biomassa saat ini, progress target, estimasi DOC 120, estimasi size 30, FCR, dan SR.
- Ringkasan per kolam memakai data sampling nyata; tidak menggunakan data dummy.
- Responsif untuk desktop, tablet, dan perangkat seluler.

## Pemasangan

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py migrate
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

`migrate` perlu tetap dijalankan karena paket proyek juga memuat migration `cultivation.0002_cycle_snapshot_and_completed_at` untuk field `final_snapshot` dari pembaruan siklus sebelumnya.

Grafik menggunakan Chart.js melalui CDN. Server aplikasi harus dapat memuat `https://cdn.jsdelivr.net` dari browser pengguna.
