# Perbaikan Final Rata-rata FCR

Kartu **Rata-rata FCR** pada menu Data Sampling sekarang dihitung dari batch/tanggal sampling terakhir dengan rumus per kolam:

`FCR = Pakan Kumulatif / Biomassa FR`

Kemudian seluruh FCR kolam pada batch terakhir dirata-ratakan. Dengan data 12/07/2026:

- 1,05
- 1,10
- 1,06
- 1,13
- 1,13
- 1,04

Rata-rata = 1,085, ditampilkan menjadi **1,09**.

Perubahan ini tidak mengubah struktur database dan tidak memerlukan migrasi.
