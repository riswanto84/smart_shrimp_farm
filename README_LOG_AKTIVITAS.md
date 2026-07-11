# Log Riwayat Aktivitas Pengguna

Fitur ini hanya dapat diakses oleh Root/Superuser dan role Owner/Owner Tambak melalui menu **Pengaturan → Log Aktivitas**.

Yang dicatat otomatis:
- login dan logout;
- tambah, edit, hapus data;
- export/unduh PDF dan Excel;
- modul, URL, metode HTTP, status respons, alamat IP, role saat aktivitas, perangkat/browser;
- metadata form yang aman. Password, token, CSRF, secret key, dan credential tidak disimpan.

Setelah update jalankan:

```bash
python manage.py migrate accounts
python manage.py check
python manage.py collectstatic --noinput
```

## Deployment VPS

```bash
source env/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart smartshrimp
sudo systemctl restart nginx
```
