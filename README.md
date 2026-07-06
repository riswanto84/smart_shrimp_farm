# SMART SHRIMP FARM - Udang Emas Nusantara

Aplikasi Django untuk admin operasional tambak, kasir penjualan, pengeluaran operasional, laporan PDF/Excel, prakiraan cuaca, Chat AI Ollama, investor dashboard, dan multi-role user.

## Login Dummy

Username: `riswanto`
Password: `admin12345`

User demo lain:
- `budi` / `12345678` : Teknisi + Kasir
- `ahmad` / `12345678` : Teknisi
- `investor.a` / `12345678` : Investor
- `akuntan` / `12345678` : Akuntan

## Jalankan di Mac / Localhost

```bash
cd smart_shrimp_farm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Buka:
- Login admin: http://localhost:8000/ atau http://localhost:8000/accounts/login/
- Login: http://localhost:8000/accounts/login/
- Dashboard: http://localhost:8000/dashboard/

## Catatan

- Database `db.sqlite3` sudah diisi data dummy awal.
- Jika database dihapus, jalankan kembali `python manage.py migrate` lalu `python manage.py seed_demo`.
- Fitur Chat AI menggunakan Ollama lokal. Pastikan Ollama aktif di `http://localhost:11434` bila ingin jawaban AI asli.
- Fitur cuaca menggunakan Open-Meteo dan membutuhkan internet.

## Update: Role-Based Access Control

Versi ini menambahkan pembatasan akses berbasis role aplikasi:

- Owner / Admin / Super Admin: semua fitur.
- Teknisi: dashboard, master kolam, parameter harian, panen, cuaca, chat AI.
- Kasir: dashboard, kasir penjualan, nota, pelanggan.
- Akuntan: dashboard, nota, pengeluaran operasional, laba rugi.
- Investor: dashboard dan dashboard investor.

Sidebar dan bottom navigation otomatis hanya menampilkan menu sesuai role pengguna. Jika user mencoba membuka URL fitur yang tidak sesuai role, aplikasi menampilkan halaman **Akses Ditolak**.

## Update 6 Juli 2026 - Login & Nota Thermal

Perbaikan yang ditambahkan:
- Halaman login profesional Udang Emas Nusantara dengan layout split-screen, background tambak, warna navy-gold, dan headline "Tambak Nusantara Untuk Kualitas Dunia!".
- Template nota thermal ukuran 80 mm untuk printer POS.
- PDF nota dibuat dalam format thermal 80 mm.
- Identitas nota:
  - Alamat: Jalan Pantai Mekar, Kec. Muara Gembong, Kabupaten Bekasi, Jawa Barat 17730
  - Telepon: 081219142796
  - Instagram: @udang.emas.nusantara
  - TikTok: udang.emas.nusantara
- Logo nota menggunakan versi thermal hitam-putih dari logo Udang Emas Nusantara.

File utama yang diubah:
- `templates/accounts/login.html`
- `templates/sales/invoice.html`
- `static/css/app.css`
- `sales/pdf.py`
- `static/img/logo_uen_thermal.png`
