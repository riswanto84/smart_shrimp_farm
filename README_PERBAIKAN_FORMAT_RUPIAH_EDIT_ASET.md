# Perbaikan Format Rupiah — Edit Aset Tetap

Tanggal: 20 Agustus 2026

## Perubahan
- Field **Harga perolehan**, **Biaya tambahan**, dan **Nilai residu** pada form Tambah/Edit Aset Tetap sekarang otomatis menggunakan format Rupiah Indonesia.
- Pemisah ribuan menggunakan titik, contoh `675.000.000`.
- Prefix `Rp` ditampilkan pada field agar nominal lebih mudah dibaca.
- Saat data lama dibuka untuk diedit, nominal langsung diformat dari nilai database, misalnya `675000000,00` menjadi `675.000.000`.
- Saat pengguna mengetik, format ribuan otomatis diterapkan.
- Saat disimpan, backend tetap menggunakan `parse_rupiah()` sehingga titik ribuan tidak mengubah nilai yang tersimpan.
- Tidak ada perubahan model database dan tidak membutuhkan migration baru.

## File yang diubah
- `templates/finance/asset_form.html`

## Catatan deployment
Setelah mengganti file di VPS, restart Gunicorn dan lakukan hard refresh browser agar JavaScript template terbaru dimuat.
