# Laporan Keuangan Per Siklus dan Periode

Perbaikan ini menambahkan dua mode pelaporan pada Neraca, Laba Rugi, dan Peredaran Bruto:

1. Berdasarkan Siklus: data transaksi hanya dari siklus yang dipilih.
2. Berdasarkan Periode: data lintas siklus berdasarkan tanggal mulai dan selesai. Default periode adalah 1 Januari sampai hari ini untuk tahun berjalan.

Ketentuan Neraca:
- Neraca tetap merupakan posisi pada satu tanggal (as of date).
- Dalam mode periode, laba berjalan dihitung mulai tanggal awal periode sampai tanggal posisi neraca.
- Dalam mode siklus, laba berjalan dan biomassa aktif dibatasi pada siklus yang dipilih.

Ekspor PDF/Excel membawa filter yang sama dengan halaman laporan.

Deployment:
```
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
Tidak ada migration database baru.
