# Perbaikan Penilaian Biologis & Estimasi Laba Akhir Siklus

Perubahan utama:

1. Aset biologis pada Neraca dinilai menggunakan harga jual rata-rata tertimbang aktual pada siklus yang dipilih.
2. Ditambahkan service terpusat `finance/services/final_cycle_profit.py`.
3. Dashboard utama menampilkan Estimasi Laba Akhir Siklus dengan simulasi harga per kg.
4. Dashboard Investor menampilkan potensi omzet, biaya akhir, utang, pajak 0,5%, laba bersih, margin, serta pembagian laba 30%/40%/30%.
5. Halaman Neraca menampilkan panel Estimasi Laba Akhir Siklus.
6. Biomassa menggunakan metode Index dan otomatis mengecualikan kolam panen total sesuai service biomassa yang sudah ada.
7. Tidak ada migration database baru.

Rumus estimasi:

- Nilai sisa udang = Biomassa Index tersisa × harga jual rata-rata/simulasi.
- Potensi omzet akhir = omzet terealisasi + nilai sisa udang.
- Estimasi biaya akhir = biaya berjalan + saldo utang belum dibayar (basis kas aplikasi).
- Pajak = 0,5% × potensi omzet akhir.
- Laba bersih akhir = potensi omzet akhir − estimasi biaya akhir − pajak.

Deploy VPS:

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
