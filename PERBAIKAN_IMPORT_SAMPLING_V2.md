# Perbaikan Import Sampling V2

Perbaikan ini memastikan seluruh kolom template import sampling tersimpan ke record yang tampil pada Data Sampling.

Perubahan utama:
- Nilai angka dari session dinormalisasi menjadi `Decimal`/`int` sebelum disimpan.
- Record lama dicari berdasarkan **kolam + tanggal**, termasuk record dengan siklus kosong atau siklus berbeda.
- Saat memilih **Perbarui data lama**, record lama dipindahkan ke siklus aktif lalu seluruh kolom import ditimpa.
- Mencegah data baru tersimpan sebagai duplikat yang tidak terlihat pada halaman pertama.

Kolom yang dipastikan tersimpan:
`ADG Weekly Target`, `Pakan Kumulatif`, `Tebar`, `F/D`, `FR`, `Populasi Index`, `Index`, dan `Catatan`.
