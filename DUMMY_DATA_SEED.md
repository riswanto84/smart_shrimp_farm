# Seed Data Dummy Smart Shrimp Farm

Command ini menyiapkan data dummy lengkap untuk kebutuhan demo aplikasi Smart Shrimp Farm.

## Perintah

```bash
python manage.py migrate
python manage.py seed_all_dummy --count 50 --reset
python manage.py runserver
```

## Login Demo

- Username: `riswanto`
- Password: `admin12345`

## Data yang dibuat

- Role, permission, user demo
- Master kolam
- Data tebar
- Data parameter air harian
- Data log pakan
- Data treatment
- Data harian kolam
- Cek anco harian
- Data sampling sesuai format Excel
- Data siphon
- Data panen
- Data pelanggan
- Nota penjualan dan item nota
- Pengeluaran operasional
- Chat AI Ollama demo

Default membuat 50 data untuk modul transaksi utama.
