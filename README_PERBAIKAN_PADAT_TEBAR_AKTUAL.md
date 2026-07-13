# Perbaikan Padat Tebar Aktual pada Dashboard

Ringkasan kolam tidak lagi menampilkan nilai hardcode `80 ekor/m²`.

## Sumber data

- `SamplingRecord.stocking_count` (kolom **Tebar**) dari batch/tanggal sampling terbaru pada siklus yang sedang dipilih.
- `Pond.area_m2` dari Master Kolam.

## Rumus

```text
Padat tebar aktual = Jumlah tebar / Luas kolam (m²)
```

Jika suatu kolam belum memiliki data tebar pada batch sampling terbaru, dashboard menampilkan **Belum ada data**, bukan angka contoh.

Tidak ada perubahan model atau migrasi database.
