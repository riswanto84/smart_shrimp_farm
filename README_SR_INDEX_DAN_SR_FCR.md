# Perbaikan Dashboard Produksi: SR Index dan SR FCR

Dashboard sebelumnya menampilkan `estimated_sr` (SR FR) dan hanya memakai SR Index sebagai fallback. Perbaikan ini memisahkan dua indikator:

- **SR Index** = Populasi Index / Tebar x 100
- **SR FCR** = (((Pakan Kumulatif / FCR) x 1000 / ABW) / Tebar) x 100

SR FCR hanya ditampilkan jika pakan kumulatif, FCR, ABW, dan jumlah tebar tersedia. Tidak ada migration database baru karena nilai dihitung saat dashboard dibuka.
