# Perbaikan Konsistensi Estimasi DOC dan Grafik Biomassa

## Perubahan

1. Card Estimasi DOC, titik akhir grafik, tooltip, dan prediksi size menggunakan nilai proyeksi yang sama dari backend.
2. Nilai proyeksi biomassa dibulatkan satu kali menjadi dua desimal.
3. Grafik menggunakan angka DOC sebagai kunci sumbu, bukan indeks array.
4. DOC yang sama tidak lagi ditampilkan berulang. Bila ada beberapa batch pada DOC yang sama, digunakan batch terbaru.
5. Nilai prediksi akhir ditulis langsung di dekat titik akhir grafik.
6. Tooltip grafik menampilkan nilai biomassa dua desimal dan detail sampling aktual secara konsisten.

## Database

Tidak ada perubahan model dan tidak diperlukan migrasi baru.
