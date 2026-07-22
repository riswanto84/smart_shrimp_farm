# Multidokumen Pengeluaran Operasional

Perubahan:
- Model `ExpenseDocument` dengan relasi ke `OperationalExpense`.
- Upload beberapa file sekaligus pada form tambah/edit pengeluaran.
- Format: PDF, JPG/JPEG, PNG, WEBP, DOC/DOCX, XLS/XLSX.
- Batas maksimum 10 MB per file.
- Daftar dokumen pada halaman edit, lengkap dengan tombol buka dan hapus.
- Jumlah dokumen tampil pada tabel Pengeluaran Operasional.
- Bukti lama pada field `receipt` tetap dipertahankan untuk kompatibilitas.

Penerapan VPS:
```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py migrate finance
python manage.py check
sudo systemctl restart smartshrimp.service
sudo systemctl reload nginx
```

Pastikan konfigurasi `MEDIA_ROOT`, `MEDIA_URL`, serta Nginx untuk `/media/` sudah aktif.
