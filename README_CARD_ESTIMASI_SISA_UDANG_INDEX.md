# Card Estimasi Sisa Udang Menggunakan Index

Perubahan pada Dashboard:

- Menambahkan satu card **Estimasi Sisa Udang (Index)**.
- Sumber biomassa awal menggunakan `SamplingRecord.biomass_index_kg`.
- Rumus per kolam aktif: `Biomassa Index sampling terakhir - panen parsial setelah sampling - biomassa mortalitas setelah sampling`.
- Biomassa mortalitas dihitung dari `jumlah udang mati x ABW / 1000`.
- Kolam yang sudah selesai panen tidak dimasukkan.
- Card Biomassa FR lama tetap dipertahankan sebagai pembanding.
- Tidak memerlukan migration database.
