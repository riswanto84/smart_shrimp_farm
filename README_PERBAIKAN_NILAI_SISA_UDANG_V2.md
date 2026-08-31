# Perbaikan Perhitungan Nilai Sisa Udang & Potensi Omzet Akhir

Perbaikan ini menyamakan sumber biomassa Index antara Dashboard dan proyeksi laba akhir.

## Masalah
Sebelumnya `calculate_final_cycle_profit()` mengambil snapshot biomassa tanpa menyebut siklus terpilih:
`calculate_index_biomass_snapshot(as_of=as_of)`

Snapshot memilih sampling terbaru per kolam. Jika sampling terbaru berasal dari siklus lain, hasil kemudian difilter berdasarkan siklus terpilih dan seluruh baris dapat menjadi kosong. Akibatnya:
- Biomassa tersisa = 0 kg
- Nilai Sisa Udang = Rp0
- Potensi Omzet Akhir hanya sama dengan omzet terealisasi.

## Perbaikan
1. `calculate_index_biomass_snapshot()` sekarang menerima parameter `cycle`.
2. `calculate_pond_index_biomass()` mencari sampling terbaru yang memang milik siklus tersebut.
3. `finance/services/final_cycle_profit.py` meminta snapshot langsung untuk `cycle` terpilih.
4. `core/views.py` juga memakai snapshot Index untuk siklus terpilih, sehingga Dashboard Produksi dan proyeksi laba memakai basis yang sama.
5. Ditambahkan informasi jumlah kolam yang menyumbang biomassa ke hasil proyeksi.

## Rumus
Biomassa Index tersisa:
`Populasi Index tersisa × ABW proyeksi / 1.000`

Populasi Index tersisa:
`Populasi Index sampling - estimasi populasi panen parsial - mortalitas siphon`

Nilai Sisa Udang:
`Biomassa Index tersisa × harga yang digunakan`

Potensi Omzet Akhir:
`Omzet terealisasi + Nilai Sisa Udang`

Harga yang digunakan:
- harga simulasi jika pengguna mengisi harga simulasi;
- jika tidak, harga transaksi panen/penjualan terbaru yang valid;
- fallback ke rata-rata penjualan siklus;
- fallback terakhir ke harga estimasi siklus.

## Catatan
Tidak ada perubahan model database dan tidak memerlukan migration.
