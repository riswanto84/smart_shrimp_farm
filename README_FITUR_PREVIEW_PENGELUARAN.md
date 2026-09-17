# Fitur Preview Dokumen Pengeluaran Operasional

Pembaruan ini menambahkan tombol **Preview** pada kolom Dokumen di daftar Pengeluaran Operasional.

## Fitur
- Preview gambar JPG/JPEG/PNG/WEBP di dalam modal.
- Preview PDF di dalam modal menggunakan viewer browser.
- File Word/Excel tetap ditampilkan dalam daftar dengan tombol Buka/Unduh.
- Mendukung beberapa dokumen pada satu pengeluaran.
- Mendukung bukti lama dari field `receipt`.
- Akses file melalui endpoint yang dilindungi login dan permission `finance.expenses`.
- Tidak memerlukan migrasi database.

## Penerapan VPS
```bash
source env/bin/activate
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
