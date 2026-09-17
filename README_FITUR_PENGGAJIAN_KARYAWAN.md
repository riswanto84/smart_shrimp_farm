# Fitur Penggajian Karyawan

Fitur baru tersedia pada menu **SDM & Penggajian**:

- Penggajian Karyawan (dashboard)
- Data Karyawan
- Periode Penggajian
- Perhitungan gaji bulanan/harian
- Gaji pokok, lembur, uang makan, transportasi, tunjangan, bonus
- Potongan BPJS, pajak, kasbon, dan potongan lain
- Status Belum Dibayar, Dibayar Sebagian, atau Lunas
- Slip gaji siap cetak
- Laporan penggajian dengan filter periode, karyawan, dan status
- Ekspor laporan ke Excel

Ketika gaji berstatus **Lunas** dan memiliki tanggal pembayaran, sistem otomatis membuat Pengeluaran Operasional kategori **Tenaga Kerja**. Dengan demikian biaya gaji masuk ke laporan Laba/Rugi melalui mekanisme pengeluaran yang sudah ada dan tidak dihitung ganda.

## Instalasi

```bash
source env/bin/activate
python manage.py migrate payroll
python manage.py check
sudo systemctl restart gunicorn
```

Lakukan backup database sebelum migration di server produksi.
