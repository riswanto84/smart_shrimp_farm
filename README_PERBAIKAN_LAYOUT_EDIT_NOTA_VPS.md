# Perbaikan layout Edit Nota di VPS

Panel ringkasan transaksi dipaksa tetap berada di sisi kanan pada layar desktop (lebar viewport CSS di atas 900 px). CSS kritis juga ditanam langsung pada template agar tidak bergantung pada cache `collectstatic`/Nginx. Pada perangkat kecil panel tetap turun ke bawah.

Setelah deploy:

```bash
python manage.py collectstatic --clear --noinput
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Lakukan hard refresh browser.
