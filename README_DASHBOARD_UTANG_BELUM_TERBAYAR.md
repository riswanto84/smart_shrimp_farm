# Dashboard Utang Belum Terbayar

Perubahan:

- Menambahkan kartu **Utang Belum Terbayar** pada Dashboard.
- Menambahkan kartu **Jatuh Tempo Bulan Ini**.
- Nilai saldo dihitung dari nilai awal utang dikurangi seluruh pembayaran.
- Perhitungan utang bersifat lintas siklus agar seluruh kewajiban usaha terlihat oleh owner.
- Kartu dapat diklik dan membuka menu Utang Usaha.
- Tidak ada perubahan database atau migration baru.

## Deploy VPS

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
