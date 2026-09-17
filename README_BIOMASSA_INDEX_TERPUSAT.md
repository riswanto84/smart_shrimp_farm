# Perbaikan Biomassa Index Terpusat

Dashboard dan Neraca sekarang memakai satu service:

`operations/services/biomass.py`

Rumus utama:

1. Populasi Index sampling terbaru diproyeksikan menggunakan ADG sampai tanggal laporan.
2. Populasi dikurangi estimasi populasi panen parsial setelah sampling.
3. Populasi dikurangi mortalitas siphon setelah sampling.
4. Biomassa Index aktual = populasi Index tersisa × ABW proyeksi / 1.000.
5. Kolam panen total, siklus selesai, atau tidak aktif dikeluarkan.

Nilai `biomass_kg`/FR tidak digunakan sebagai dasar perhitungan. Fallback hanya dilakukan untuk memperoleh populasi Index ketika data populasi Index kosong tetapi `biomass_index_kg` tersedia.

Tidak ada migration baru.
