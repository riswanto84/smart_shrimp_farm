# Update Dashboard Panen Riil

Dashboard utama kini menampilkan data panen yang benar-benar sudah dilakukan pada siklus terpilih.

## Sumber data
- Berat panen riil: `operations.Harvest.total_kg`
- Target produksi: `CultivationCycle.target_biomass_ton`
- Omzet dan berat penjualan: transaksi `sales.Sale` yang valid pada siklus terpilih

## Tampilan baru
- Total panen riil (kg dan ton)
- Jumlah kegiatan panen
- Target produksi dan sisa target
- Persentase progres target
- Omzet siklus
- Harga jual rata-rata
- Grafik panen per tanggal
- Tabel delapan riwayat panen terbaru

Tidak ada perubahan model atau migrasi database.
