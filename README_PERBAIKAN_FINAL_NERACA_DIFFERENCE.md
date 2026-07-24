# Perbaikan Final Neraca

Perbaikan:
- Menulis ulang seluruh `_balance_sheet_data()`.
- Variabel `difference` selalu dihitung sebelum digunakan.
- Tidak ada akun rekonsiliasi otomatis.
- Total Ekuitas = Ekuitas Pembukaan + Laba/Rugi Tahun Berjalan.
- Status neraca: Seimbang, Saldo Awal Belum Direkonsiliasi, atau Tidak Seimbang.
- Tidak ada perubahan model/database.
- Tidak memerlukan makemigrations atau migrate.

Setelah deploy:
```bash
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```
