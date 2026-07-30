# Penambahan Field Catatan Payroll

Perubahan:
- Menambahkan field `catatan` pada `PayrollRecord`.
- Field Catatan terpisah dari field Keterangan.
- Catatan tampil pada form tambah/edit gaji dan slip gaji.
- Catatan ikut disalin ke keterangan Pengeluaran Operasional ketika payroll lunas.

Perintah VPS:
```bash
python manage.py check
python manage.py migrate payroll
sudo systemctl restart gunicorn
```
