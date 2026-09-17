# Perbaikan Target Populasi Hidup dalam Persen

- Field input **Target Populasi Hidup (ekor)** dihapus dari form Siklus Budidaya.
- Diganti menjadi **Target Populasi Hidup (SR) (%)** dengan rentang 0,01–100.
- Target populasi hidup dalam ekor dihitung otomatis: `total tebar × target SR / 100`.
- Field database lama `target_population` tetap dipertahankan agar kompatibel dengan data dan migration lama, tetapi tidak lagi ditampilkan atau diinput.
- Tidak memerlukan migration database.
