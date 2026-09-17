# Penambahan Carrying Capacity (CC)

Perbaikan ini menambahkan perhitungan Carrying Capacity pada dashboard tanpa migrasi database.

Rumus:

```text
CC (ton) = Index sampling terbaru (kg/m2) x luas kolam (m2) / 1.000
```

Perubahan:
- Card total CC pada bagian Realisasi Panen Riil.
- Tabel CC per kolam berisi luas, Index terbaru, CC ton dan kg.
- Hanya kolam aktif dengan sampling terbaru yang dihitung.
- CC tidak dikurangi panen karena merupakan kapasitas kolam, bukan biomassa aktual tersisa.
