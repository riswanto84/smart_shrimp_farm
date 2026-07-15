# Perbaikan Target Size AI Prediksi Panen

Dropdown **Target Size** pada menu **AI Prediksi Panen Parsial** sekarang menyediakan pilihan:

`100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25` ekor/kg.

Ketentuan:
- Urutan dimulai dari size 100 sampai size 25.
- Setiap pilihan turun 5 angka.
- Backend hanya menerima nilai dari daftar tersebut.
- Nilai URL yang tidak valid otomatis kembali ke default size 70.
- Tidak ada perubahan struktur database dan tidak perlu migrasi.
