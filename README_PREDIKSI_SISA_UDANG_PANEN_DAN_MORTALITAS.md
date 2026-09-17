# Prediksi Sisa Udang: Panen Parsial dan Mortalitas

Perbaikan pada dashboard **Prediksi Pertumbuhan per Kolam**:

- Kolam dengan panen total tidak dimasukkan ke prediksi.
- Panen parsial setelah sampling terakhir mengurangi populasi berdasarkan `berat panen × size panen`.
- Udang mati pada pencatatan siphon setelah sampling terakhir mengurangi populasi tersisa berdasarkan `dead_count`.
- Biomassa prediksi dihitung ulang dari populasi tersisa × ABW prediksi.
- Dashboard menampilkan populasi saat sampling, pengurangan panen parsial, mortalitas, dan populasi akhir.

Tidak ada perubahan model maupun migration database.
