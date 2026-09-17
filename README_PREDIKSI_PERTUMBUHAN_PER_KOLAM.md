# Prediksi Pertumbuhan per Kolam

Pembaruan menambahkan halaman `/operations/growth-prediction/` dan menu **Prediksi Pertumbuhan**.

## Sumber data
- DOC, ABW, size, ADG, FCR, biomassa, populasi: `SamplingRecord` pada siklus terpilih.
- Target ADG, target DOC, dan durasi: `CultivationCycle`.

## Logika prediksi
- Satu record terbaru digunakan untuk setiap DOC agar duplikasi sampling tidak menggandakan titik.
- ADG prediksi dihitung dari slope ABW maksimal empat sampling terakhir.
- Fallback: ADG aktual terakhir, ADG kumulatif, lalu target ADG siklus.
- Prediksi size = 1000 / ABW prediksi.
- Prediksi biomassa memakai populasi sampling terakhir dan tidak mengasumsikan perubahan SR berikutnya.

## Fitur tampilan
- Grafik prediksi size semua kolam.
- Grafik aktual vs prediksi per kolam.
- Grafik ABW dan biomassa.
- Timeline target size 100, 80, 70, 60, 50, 40, dan 30.
- KPI DOC, size, ADG, biomassa, dan status pertumbuhan.
- Filter kolam dan horizon DOC 120/135/150/180.

Tidak memerlukan migrasi database.
