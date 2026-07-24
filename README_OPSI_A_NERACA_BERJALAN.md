# Opsi A — Saldo Awal dan Neraca Berjalan

Perubahan:
- Saldo Awal hanya menghitung posisi pembukaan.
- Modal Pemilik tidak dipengaruhi laba/rugi tahun berjalan.
- Neraca berjalan memasukkan laba/rugi tahun berjalan ke Total Ekuitas.
- Total Ekuitas Berjalan = Ekuitas Awal + Laba/Rugi Tahun Berjalan.
- Tidak ada perubahan model atau database.
- Tidak memerlukan makemigrations atau migrate.

Setelah deploy:
```bash
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```
