# Perbaikan Aset Biologis Neraca

Rumus biomassa aktual per kolam:

1. Proyeksi ABW = ABW sampling terakhir + (ADG aktual x umur data sampling)
2. Populasi tersisa = populasi sampling - populasi panen parsial - mortalitas siphon
3. Biomassa aktual = populasi tersisa x proyeksi ABW / 1.000
4. Nilai aset biologis = biomassa aktual x harga penjualan aktual untuk size terdekat

Fallback harga: estimasi harga siklus, kemudian rata-rata seluruh penjualan.
Kolam panen total, siklus selesai, atau tidak aktif tidak dihitung.

Indikator per kolam: Biomassa, Sampling, Harga, SR, ADG, dan FCR.

Deploy:
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx

Tidak ada migration database baru.
