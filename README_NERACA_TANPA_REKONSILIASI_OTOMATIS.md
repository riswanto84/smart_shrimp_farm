# Perbaikan Neraca Tanpa Rekonsiliasi Otomatis

Perubahan utama:
- Menghapus akun rekonsiliasi otomatis dari neraca.
- Selisih neraca ditampilkan apa adanya.
- Total Ekuitas Berjalan = Ekuitas Pembukaan + Laba/Rugi Tahun Berjalan.
- Saldo Awal tidak memakai laba/rugi tahun berjalan.
- Status neraca:
  - Seimbang
  - Saldo Awal Belum Direkonsiliasi
  - Tidak Seimbang
- Tidak ada perubahan model atau database.
- Tidak memerlukan makemigrations atau migrate.

Setelah deploy:
```bash
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```
