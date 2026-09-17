# Perbaikan Penguncian Siklus Selesai

Perbaikan ini memastikan siklus berstatus **Selesai** benar-benar menjadi arsip read-only.

## Fitur operasional yang dikunci

- Parameter Harian
- Data Harian Kolam
- Cek Anco Harian
- Data Sampling
- Data Siphon
- Data Panen
- Import Excel operasional

Untuk seluruh modul tersebut, akses **tambah, edit, hapus, dan import** diblokir pada sisi server. Pengguna tidak dapat melewati penguncian dengan membuka URL aksi secara langsung.

## Perilaku data lama

- Record yang sudah memiliki `cycle` diperiksa berdasarkan siklus record tersebut.
- Record lama dengan `cycle=NULL` diperiksa berdasarkan siklus yang sedang dipilih.
- Record dari siklus lain tidak dapat dipindahkan melalui URL edit.
- Detail, filter, export Excel, dan cetak PDF tetap dapat digunakan.

## Pemasangan

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

Tidak ada perubahan model atau database, sehingga tidak diperlukan migrasi.
