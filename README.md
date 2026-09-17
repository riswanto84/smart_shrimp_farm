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

## Integrasi Midtrans Snap

Fitur pembayaran online Midtrans sudah ditambahkan pada menu detail nota penjualan.

### 1. Konfigurasi environment

Isi variabel berikut di `.env` atau environment server:

```env
MIDTRANS_IS_PRODUCTION=False
MIDTRANS_SERVER_KEY=SB-Mid-server-xxxxxxxxxxxxxxxx
MIDTRANS_CLIENT_KEY=SB-Mid-client-xxxxxxxxxxxxxxxx
MIDTRANS_MERCHANT_ID=Gxxxxxxxxx
APP_BASE_URL=https://domain-anda.com
```

Untuk uji coba lokal, gunakan Sandbox Midtrans. Jika aplikasi masih berjalan di localhost dan ingin menerima webhook, gunakan domain publik seperti ngrok lalu isi `APP_BASE_URL` dengan URL ngrok tersebut.

### 2. Jalankan migrasi

```bash
python manage.py migrate
```

### 3. Alur pembayaran

1. Kasir membuat nota seperti biasa.
2. Buka detail nota.
3. Klik **Bayar Online Midtrans**.
4. Pelanggan diarahkan ke halaman pembayaran Midtrans Snap.
5. Midtrans mengirim notifikasi ke webhook Django.
6. Status nota berubah otomatis menjadi **Menunggu Pembayaran**, **Lunas**, **Expired**, **Gagal**, atau **Dibatalkan**.

### 4. URL webhook Midtrans

Atur Payment Notification URL di dashboard Midtrans ke:

```text
https://domain-anda.com/sales/midtrans/notification/
```

Jika menggunakan ngrok:

```text
https://abc123.ngrok-free.app/sales/midtrans/notification/
```

### 5. Tombol tambahan di nota

Pada detail nota tersedia tombol:

- **Bayar Online Midtrans**: membuat transaksi Snap.
- **Buka Link Bayar**: membuka kembali halaman pembayaran Midtrans jika transaksi masih pending.
- **Cek Status**: mengecek status terbaru ke Midtrans Status API.
- **Kirim PDF WhatsApp**: membagikan file PDF nota ke WhatsApp pelanggan.

## Update: Laporan Keuangan Periodik

Fitur baru ditambahkan pada menu **Keuangan > Laporan Keuangan Periodik**.

Fitur utama:
- Tab laporan: Harian, Mingguan, Bulanan, Per Siklus, dan Piutang.
- Filter rentang tanggal, kolam, metode pembayaran, dan status nota.
- KPI: Total Omzet, Total Pengeluaran, Laba Bersih, Piutang Belum Lunas.
- Grafik perbandingan omzet vs pengeluaran.
- Grafik komposisi biaya operasional.
- Aging piutang pelanggan.
- Ringkasan laporan dan highlight otomatis.
- Export Excel dan PDF.

URL fitur:
- `/finance/periodic-report/`
- `/finance/periodic-report/export/excel/`
- `/finance/periodic-report/export/pdf/`

Role yang bisa mengakses:
- Owner/Admin otomatis bisa mengakses semua fitur.
- Role `akuntan` ditambahkan permission `finance.periodic_report`.

## Update laporan PDF manajemen
- Export PDF Laporan Keuangan Periodik dibuat ulang dengan format profesional untuk manajemen.
- PDF mencakup header brand Udang Emas Nusantara, ringkasan filter, KPI, ringkasan eksekutif, tabel utama, komposisi biaya, metode pembayaran, dan catatan manajemen.
- File utama yang berubah: `finance/views.py`.

## Update Modul Operasional Inti Smart Shrimp Farm

Fitur operasional inti yang ditambahkan:

1. **Dashboard Produksi**
   - Ringkasan alur Data Tebar → Data Harian Pakan → Cek Anco → Sampling → Siphon → Estimasi Panen.
   - KPI produksi: populasi tebar, pakan hari ini, ABW rata-rata, alert anco/mortalitas.
   - Kondisi terbaru per kolam dan insight operasional.

2. **Data Harian Kolam**
   - Tanggal, kolam, DOC, kode pakan, pakan harian, air masuk, cuaca, treatment, catatan teknisi.
   - Export Excel.

3. **Cek Anco Harian**
   - Cek pagi/siang/sore untuk Anco 1 dan Anco 2.
   - Status: H = Habis, S = Sisa, SS = Sisa Sedikit.
   - Analisa otomatis status appetite dan rekomendasi pakan.

4. **Data Sampling**
   - ABW, size, ADG mingguan, ADG akumulatif, SR estimasi, biomassa, FCR, populasi, pakan kumulatif, FR, index, estimasi panen.
   - Sebagian metrik dihitung otomatis dari data tebar dan pakan harian bila field dikosongkan/0.
   - Export Excel dan PDF.

5. **Data Siphon**
   - Udang mati, udang hidup ikut tersiphon, jumlah harian, total akumulatif, tren/indikator kesehatan kolam.
   - Export Excel dan PDF.

Setelah mengganti source code, jalankan:

```bash
python manage.py migrate
python manage.py runserver
```
