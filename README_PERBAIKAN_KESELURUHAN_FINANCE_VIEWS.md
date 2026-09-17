# Perbaikan keseluruhan finance/views.py

- Semua pemanggilan tanggal memakai `_safe_parse_date()`.
- Mendukung string ISO, `date`, `datetime`, kosong, dan input tidak valid.
- Import `date` dan `datetime` diperbaiki dari modul standar `datetime`.
- Tidak mengubah model maupun database.
- Tidak perlu makemigrations/migrate.
