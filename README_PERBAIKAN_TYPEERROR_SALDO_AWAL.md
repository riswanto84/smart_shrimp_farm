# Perbaikan TypeError Saldo Awal

Error:
`fromisoformat: argument must be str`

Penyebab:
`django.utils.dateparse.parse_date()` menerima objek `date`/`datetime`, sedangkan fungsi tersebut hanya menerima string.

Perbaikan:
- Menambahkan `_safe_parse_date()`.
- Mendukung input `str`, `date`, `datetime`, nilai kosong, dan nilai tidak valid.
- Tidak mengubah model atau database.
- Tidak membutuhkan `makemigrations` maupun `migrate`.

Setelah deploy:
```bash
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```
