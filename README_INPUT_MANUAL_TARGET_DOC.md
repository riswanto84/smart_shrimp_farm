# Input Manual Target DOC

Perubahan pada halaman **Prediksi Pertumbuhan per Kolam**:

- Dropdown target DOC diganti menjadi input angka manual.
- Nilai minimal mengikuti DOC sampling terakhir kolam terpilih.
- Nilai maksimal DOC 250.
- Nilai bukan angka otomatis kembali ke target DOC siklus/default.
- Backend tetap memvalidasi nilai sehingga manipulasi query string tidak menghasilkan target DOC yang tidak valid.
- Tidak memerlukan migrasi database.
