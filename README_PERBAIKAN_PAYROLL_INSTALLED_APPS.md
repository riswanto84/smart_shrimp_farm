# Perbaikan registrasi aplikasi Payroll

Error yang diperbaiki:

```
RuntimeError: Model class payroll.models.Employee doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS.
```

Perubahan:
- `payroll.apps.PayrollConfig` didaftarkan secara eksplisit di `INSTALLED_APPS`.
- `payroll/__init__.py` menunjuk ke `PayrollConfig` sebagai kompatibilitas tambahan.
- Modul payroll, URL, model, form, template, admin, dan migration tetap disertakan.

## Instalasi di VPS

Jangan hanya menyalin folder `payroll`. Pastikan seluruh ZIP diekstrak/ditimpa ke root proyek sehingga `smart_shrimp_farm/settings.py` ikut terbarui.

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
python manage.py showmigrations payroll
python manage.py migrate payroll
sudo systemctl restart gunicorn
```

Jika service berbeda, sesuaikan nama service Gunicorn.
