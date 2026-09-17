# Perbaikan ModuleNotFoundError: payroll.apps

Jika muncul:

`ModuleNotFoundError: No module named 'payroll.apps'`

versi ini mengubah `INSTALLED_APPS` dari:

`payroll.apps.PayrollConfig`

menjadi:

`payroll`

Django tetap akan membaca `PayrollConfig` dari `payroll/apps.py` jika file tersebut tersedia, tetapi konfigurasi ini juga lebih kompatibel dengan instalasi/deployment lama.

## Setelah menyalin ZIP

Pastikan berada di folder yang berisi `manage.py`, lalu:

```bash
source venv/bin/activate
python3 manage.py check
python3 manage.py migrate payroll
python3 manage.py runserver
```

Jika `migrate payroll` menyatakan tidak ada migrasi yang perlu dijalankan, itu normal.

## Jika error tetap muncul

Jalankan:

```bash
pwd
ls -la payroll
python3 -c "import payroll; print(payroll.__file__)"
```

Folder `payroll` harus berada sejajar dengan `manage.py`, bukan berada di dalam folder proyek lain.
