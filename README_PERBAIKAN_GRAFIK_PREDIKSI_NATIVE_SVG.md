# Perbaikan Grafik Prediksi Pertumbuhan

Perbaikan ini diterapkan langsung pada ZIP `smart_shrimp_farm(14).zip`.

## Akar masalah yang ditemukan
Template `templates/operations/growth_prediction_dashboard.html` pada ZIP terakhir masih memuat Chart.js dari CDN jsDelivr. Ketika library tersebut tidak berhasil dimuat, elemen canvas tetap kosong tanpa grafik.

## Perbaikan
- Menghapus ketergantungan Chart.js/CDN.
- Mengganti tiga canvas menjadi grafik SVG native:
  - Perbandingan prediksi size semua kolam.
  - Size aktual vs prediksi kolam terpilih.
  - ABW dan biomassa prediksi.
- Grafik membaca data yang sama dari `json_script` Django.
- Menampilkan pesan apabila data grafik kosong.
- Tidak memerlukan migrasi database maupun collectstatic.

## Deployment
```bash
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```
Lakukan hard refresh browser setelah restart.
