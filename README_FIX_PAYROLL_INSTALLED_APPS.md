# Perbaikan error payroll tidak terdaftar

Error yang diperbaiki:

`RuntimeError: Model class payroll.models.Employee ... isn't in an application in INSTALLED_APPS.`

## Perubahan

- Memastikan `payroll.apps.PayrollConfig` tercantum di `INSTALLED_APPS` pada `smart_shrimp_farm/settings.py`.
- Menambahkan deklarasi kompatibilitas pada `payroll/__init__.py`.
- Tidak menghapus atau mengubah migration dan data yang sudah ada.

## Cara memasang di VPS

Ekstrak ZIP dan timpa folder proyek yang digunakan Gunicorn. Pastikan file berikut benar-benar ikut tertimpa:

- `smart_shrimp_farm/settings.py`
- `payroll/__init__.py`
- seluruh folder `payroll/`

Lalu jalankan dari folder yang berisi `manage.py`:

```bash
source env/bin/activate
python manage.py check
python manage.py migrate payroll
python manage.py migrate
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Jika nama service Gunicorn berbeda, gunakan nama service VPS yang berlaku.

## Pemeriksaan cepat

```bash
python manage.py shell -c "from django.conf import settings; print([x for x in settings.INSTALLED_APPS if 'payroll' in x])"
```

Hasil yang benar:

```text
['payroll.apps.PayrollConfig']
```
