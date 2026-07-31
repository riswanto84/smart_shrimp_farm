# Perbaikan Neraca: Aset Biologis di Kolam

Perubahan:
- Neraca mengakui biomassa udang aktif sebagai aset lancar biologis.
- Biomassa memakai `biomass_index_kg` sampling terakhir per kolam (fallback `biomass_kg`).
- Harga memakai `estimated_price_per_kg` pada siklus; jika kosong memakai rata-rata tertimbang harga penjualan aktual.
- Rincian setiap kolam menampilkan biomassa, harga, ABW, SR, DOC, tanggal sampling, dan nilai aset.
- Indikator warna:
  - Hijau: sampling maksimal 14 hari.
  - Kuning: sampling 15–30 hari.
  - Merah: sampling lebih dari 30 hari, biomassa kosong, atau harga belum tersedia.
  - Abu-abu: kolam tidak aktif.
- Total aset biologis masuk ke Aset Lancar, Total Aset, komposisi aset, validasi otomatis, dan PDF Neraca.

Tidak ada perubahan model atau migration database.
