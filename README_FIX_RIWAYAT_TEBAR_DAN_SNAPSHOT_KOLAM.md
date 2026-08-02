# Perbaikan Riwayat Siklus

- Jumlah tebar per kolam memprioritaskan `operations.Stocking.seed_count`.
- Data impor/lama yang tidak mempunyai baris Stocking memakai `SamplingRecord.stocking_count` sebagai fallback.
- Total tebar siklus dijumlahkan dari angka final per kolam agar tidak double count.
- Kondisi akhir kolam memakai sampling terakhir masing-masing kolam, bukan satu tanggal sampling global.
- Kolam yang selesai panen lebih dahulu tetap menampilkan ABW, Size, ADG, FCR, SR, dan biomassa terakhir sebelum panen.
- Halaman dan Excel menampilkan sumber tebar serta tanggal/DOC sampling akhir.
