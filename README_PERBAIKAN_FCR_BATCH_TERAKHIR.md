# Perbaikan Kartu Rata-rata FCR

Kartu **Rata-rata FCR** pada menu Data Sampling sekarang dihitung hanya dari
satu batch/tanggal sampling paling baru yang sama untuk seluruh kolam.

Contoh batch 12/07/2026:

- K1: 1,05
- K2: 1,10
- K3: 1,06
- K5: 1,13
- K6: 1,13
- K7: 1,04

Rata-rata = 6,51 / 6 = 1,085, ditampilkan menjadi **1,09**.

Record duplikat pada kolam dan tanggal yang sama dipilih secara konsisten,
dengan memprioritaskan siklus aktif/terpilih.
