# Perbaikan Perhitungan CC berdasarkan Biomassa Index

Rumus yang diterapkan:

CC (kg/m2) = biomassa tersisa metode Index (kg) / luas kolam (m2)

Ketentuan:
- Biomassa berasal dari `biomass_index_kg` pada sampling terbaru.
- Panen parsial dan mortalitas setelah sampling terakhir dikurangkan.
- Kolam yang sudah panen total/selesai tidak dihitung.
- CC ditampilkan per kolam dalam kg/m2.
- Nilai ringkasan dashboard merupakan rata-rata tertimbang: total biomassa Index tersisa / total luas kolam aktif.
- Tidak ada perubahan model atau migrasi database.
