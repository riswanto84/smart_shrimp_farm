# Perbaikan Template Import Cek Anco Harian

Template dan parser import Cek Anco Harian telah diselaraskan dengan data pada tabel aplikasi.

## Kolom template terbaru

1. Tanggal
2. Kolam
3. Kode Pakan
4. DOC
5. P/H
6. Pagi A1
7. Pagi A2
8. Siang A1
9. Siang A2
10. Sore A1
11. Sore A2
12. Air Masuk (cm)
13. Cuaca
14. Treatment
15. Catatan

Nilai status yang diterima: `H`, `S`, `SS`, dan `-`.

Status nafsu makan dan rekomendasi tidak perlu diisi di Excel karena dihitung otomatis oleh aplikasi dari hasil cek anco.

## Perbaikan proses import

- Air Masuk sekarang dibaca dan disimpan ke `water_in_cm`.
- Cuaca sekarang dibaca dan disimpan ke `weather`.
- Header lama tetap didukung melalui alias parser.
- Data lama dapat diperbarui menggunakan opsi **Perbarui data lama**.
- Tidak ada perubahan struktur database sehingga migrasi tidak diperlukan.
