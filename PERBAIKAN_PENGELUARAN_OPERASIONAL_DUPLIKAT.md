# Perbaikan Pengeluaran Operasional

Perbaikan ini mengatasi `IntegrityError duplicate key` pada Pengeluaran Operasional.

- Menghapus unique constraint lama yang membatasi transaksi pada tanggal/kolam yang sama.
- Pengeluaran operasional tetap boleh memiliki beberapa transaksi pada tanggal dan kolam yang sama.
- Data lama yang belum mempunyai siklus dikaitkan ke siklus aktif/tersedia.
- Urutan data tetap dari tanggal terbaru ke tanggal terlama.

Jalankan:

```bash
python3 manage.py check
python3 manage.py migrate
python3 manage.py collectstatic --noinput
```
