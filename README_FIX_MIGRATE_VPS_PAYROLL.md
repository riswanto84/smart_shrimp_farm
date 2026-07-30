# Perbaikan migrasi Payroll di VPS

Masalah awal terjadi karena model `payroll` diimpor dari URL tetapi aplikasi tidak terbaca dalam `INSTALLED_APPS` aktif. Paket ini memastikan `payroll.apps.PayrollConfig` terdaftar.

Karena localhost menggunakan SQLite sedangkan VPS umumnya memakai PostgreSQL melalui `.env`, paket ini juga menambahkan `psycopg2-binary==2.9.10` ke `requirements.txt`. Perbedaan driver/database ini sering membuat localhost normal tetapi VPS gagal.

## Pemasangan aman di VPS

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
pip install -r requirements.txt
chmod +x diagnose_and_migrate_vps.sh
./diagnose_and_migrate_vps.sh
```

Skrip akan berhenti pada error pertama dan menyimpan traceback lengkap ke file `migrate_vps_YYYYMMDD_HHMMSS.log`.

Setelah berhasil:

```bash
sudo systemctl restart gunicorn
sudo systemctl reload nginx
sudo journalctl -u gunicorn -n 100 --no-pager
```

Jika nama service bukan `gunicorn`, gunakan nama service aplikasi yang ada di VPS, misalnya:

```bash
systemctl list-units --type=service | grep -Ei 'gunicorn|shrimp|uen'
```

Jangan menjalankan migrasi melalui halaman web/panel karena pesan Python sering ditampilkan hanya sebagai `Internal Server Error`.
