# Perbaikan Nilai Sisa Udang – Harga Panen Terbaru

Nilai Sisa Udang, Penilaian Biologis, dan Estimasi Laba Akhir Siklus kini menggunakan harga transaksi panen/penjualan valid yang paling baru pada siklus terpilih.

Urutan sumber harga:
1. Harga rata-rata tertimbang item pada nota penjualan terbaru.
2. Harga nota terbaru (`total_amount / total_kg`) untuk data lama tanpa SaleItem.
3. Harga rata-rata tertimbang seluruh penjualan siklus.
4. Harga estimasi siklus.

Transaksi berstatus Gagal, Expired, Dibatalkan, atau Refund tidak digunakan.
