# Modul Keuangan & Pajak Ringkas

Modul ini menambahkan fitur yang difokuskan untuk penyusunan data pajak:

1. Ringkasan pajak
2. Laporan peredaran bruto dari penjualan dan pendapatan lain
3. Laporan laba rugi dengan penanda biaya deductible/non-deductible
4. Neraca sederhana berbasis saldo pos neraca dan laba tahun berjalan
5. Daftar aset tetap
6. Perhitungan penyusutan fiskal garis lurus
7. Ekspor PDF/Excel pada laporan utama

## Instalasi

```bash
source env/bin/activate
python manage.py migrate
python manage.py check
python manage.py collectstatic --noinput
```

Kemudian restart Gunicorn/Nginx pada VPS.

## Catatan

- Penjualan berstatus Gagal, Expired, Dibatalkan, dan Refund tidak masuk peredaran bruto.
- Pendapatan lain dicatat melalui menu Peredaran Bruto.
- Saldo neraca dimasukkan per tanggal posisi. Aplikasi mengambil saldo terbaru setiap akun sampai tanggal laporan.
- Laba/rugi tahun berjalan dihitung dari peredaran bruto dikurangi pengeluaran operasional.
- Penyusutan fiskal menggunakan metode garis lurus dan masa manfaat kelompok aset yang dipilih.
- Hasil merupakan alat bantu administrasi dan tetap perlu diverifikasi dengan bukti transaksi serta penasihat pajak.
