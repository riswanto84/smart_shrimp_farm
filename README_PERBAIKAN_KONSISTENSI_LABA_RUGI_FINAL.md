# Perbaikan Konsistensi Laba/Rugi Final

Perbaikan ini memastikan Dashboard, Laporan Laba/Rugi, Laba Rugi Pajak, dan
Laba/Rugi Operasional pada Neraca memakai konteks transaksi yang sama.

## Perubahan

1. Neraca memakai seluruh transaksi yang terhubung ke siklus terpilih sampai
   tanggal posisi neraca, tanpa filter tambahan `cycle.start_date`.
2. Laba Rugi Pajak tanpa filter eksplisit memakai siklus terpilih sampai hari
   ini, sama seperti Dashboard.
3. Laporan Laba/Rugi tanpa tanggal akhir dibatasi sampai hari ini.
4. Baris `Penyusutan Aset (otomatis)` yang menduplikasi kategori `Penyusutan`
   dihapus. Penyusutan tetap dihitung satu kali melalui OperationalExpense.
5. Penyesuaian nilai wajar biomassa tetap disajikan terpisah. Angka yang harus
   sama antarmodul adalah `Laba/Rugi Operasional`.
