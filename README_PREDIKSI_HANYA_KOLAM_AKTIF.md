# Prediksi Pertumbuhan Hanya Kolam Aktif

Perbaikan:
- Kolam dengan panen `Total`, `Final`, `Panen Total`, `Panen Final`, atau `Selesai` tidak masuk dropdown dan grafik prediksi.
- Panen parsial tetap diprediksi.
- Panen parsial setelah sampling terakhir mengurangi populasi proyeksi berdasarkan berat panen × size panen.
- Jika size panen parsial kosong, digunakan size sampling terakhir.
- Sampling dan grafik semua kolam otomatis mengecualikan kolam selesai panen.
- Halaman menampilkan jumlah kolam selesai panen yang dikeluarkan.
- Tidak memerlukan migrasi database.

Setelah deploy:
```bash
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```
