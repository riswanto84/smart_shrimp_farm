# Update Dashboard Grafik Pakan dari Cek Anco

Pembaruan ini menambahkan analisis pemberian pakan pada Dashboard Produksi dengan sumber utama field P/H (`AncoCheck.daily_feed_kg`) pada menu Cek Anco.

## Fitur
- KPI pakan tanggal terbaru dan tanggal sebelumnya.
- Selisih pakan dalam kg dan persentase.
- Pakan kumulatif selama siklus terpilih.
- Rata-rata pakan harian seluruh kolam.
- Grafik pakan harian dan kumulatif (30 tanggal terakhir).
- Grafik akumulasi pakan per kolam.
- Grafik pakan dibanding biomassa, ADG, dan FCR pada tanggal sampling yang sama.
- Tabel rincian P/H, DOC, status nafsu makan, dan catatan per kolam pada tanggal terbaru.
- Seluruh query mengikuti siklus budidaya yang sedang dipilih.

## Database
Tidak ada perubahan model dan tidak membutuhkan migrasi baru.

## Penerapan di VPS
```bash
source env/bin/activate
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
