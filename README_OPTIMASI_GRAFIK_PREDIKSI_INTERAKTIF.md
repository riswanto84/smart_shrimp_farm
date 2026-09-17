# Optimasi Grafik Prediksi Pertumbuhan

Perubahan:
- Grafik Perbandingan Prediksi Size Semua Kolam memiliki tooltip interaktif per titik.
- Tooltip menampilkan kolam, status, tanggal, DOC, ABW, size, biomassa Index, ADG, FCR, SR Index, populasi, dan sumber data.
- Titik sampling aktual dibedakan dari titik proyeksi.
- Grafik Size Aktual vs Prediksi dibuat selebar penuh.
- Grafik ABW dan Biomassa Prediksi dibuat selebar penuh.
- Area proyeksi diberi shading biru muda.
- Marker panen, target size, dan target DOC diringkas agar tidak bertumpuk; detail tersedia melalui tooltip.
- Layout responsif untuk desktop dan perangkat seluler.

Tidak ada migration database baru.

Deployment:
1. python manage.py check
2. python manage.py collectstatic --noinput
3. sudo systemctl restart gunicorn
4. sudo systemctl reload nginx
