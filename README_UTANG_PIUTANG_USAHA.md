# Fitur Utang dan Piutang Usaha

## Fitur
- Daftar piutang pelanggan dan utang supplier.
- Nomor dokumen, tanggal transaksi, jatuh tempo, nilai awal, dan catatan.
- Pembayaran bertahap dengan validasi agar tidak melebihi saldo.
- Status otomatis: Belum Dibayar, Sebagian, Lunas, atau Lewat Jatuh Tempo.
- Analisis umur saldo: belum jatuh tempo, 1–30, 31–60, 61–90, dan lebih dari 90 hari.
- Pencarian dan filter status.
- Ekspor PDF.
- Saldo piutang otomatis masuk Aset pada Neraca.
- Saldo utang otomatis masuk Kewajiban pada Neraca.
- Dashboard pajak menampilkan total dan saldo lewat jatuh tempo.

## Instalasi
```bash
python manage.py migrate
python manage.py check
python manage.py collectstatic --noinput
```

Pada VPS:
```bash
sudo systemctl restart smartshrimp
sudo systemctl restart nginx
```

Migrasi baru: `finance.0006_trade_accounts`.

Catatan: pos manual Neraca dengan kelompok `Piutang Usaha` dan `Utang Usaha` tidak ikut dihitung agar tidak terjadi penghitungan ganda. Saldo kedua akun tersebut berasal dari modul ini.
