# Perbaikan Carrying Capacity (CC)

Dashboard kini menghitung CC sesuai rumus teknisi tambak:

```text
CC (kg/m²) = Estimasi Biomassa Tersisa (kg) / Luas Kolam (m²)
```

Implementasi berlaku untuk dua metode biomassa:

- CC FR menggunakan biomassa FR tersisa.
- CC Index menggunakan biomassa Index tersisa.

Biomassa tersisa telah dikurangi panen parsial dan mortalitas setelah sampling. Kolam panen total/selesai tidak masuk perhitungan. Luas diambil dari `Pond.area_m2`; bila luas nol atau belum diisi, CC ditampilkan 0.

Tidak ada perubahan model maupun migration database.
