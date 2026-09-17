# Seed data operasional Smart Shrimp Farm

Perintah ini membuat data demo untuk modul operasional dan penjualan:

```bash
python manage.py seed_operational_data --count 50 --reset
```

Data yang dibuat:
- 50 data Cek Anco Harian
- 50 data Sampling
- 50 data Siphon
- 50 data Panen
- 50 data Nota Penjualan

Catatan:
- Jalankan `python manage.py migrate` terlebih dahulu.
- Jika belum ada data kolam, jalankan `python manage.py seed_demo --count 50 --reset` terlebih dahulu.
- Opsi `--reset` menghapus data demo operasional/penjualan terkait sebelum membuat data baru.
