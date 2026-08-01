# Perbaikan Konsistensi Laba/Rugi

Perbaikan ini menjadikan `finance/services/profit_loss.py` sebagai satu-satunya sumber perhitungan laba/rugi operasional.

Digunakan oleh:
- Dashboard utama
- Laporan Laba/Rugi
- Neraca (Laba/Rugi Operasional Tahun Berjalan)

Kebijakan perhitungan:
- Pendapatan = penjualan valid + pendapatan lain.
- Pengeluaran = seluruh `OperationalExpense` non-kapital, termasuk kategori Penggajian dan Penyusutan yang sudah diposting.
- Penyusutan tidak dihitung lagi dari daftar aset pada laba/rugi agar tidak terjadi double counting. Akumulasi penyusutan daftar aset tetap digunakan untuk nilai buku aset di Neraca.
- Neraca memakai siklus terpilih dan batas tanggal posisi neraca.
- Perubahan nilai wajar biomassa tetap disajikan terpisah sebagai penilaian biologis, bukan dicampur dengan laba operasional.

Deploy:
```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Tidak ada migration baru.
