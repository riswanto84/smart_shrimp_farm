# Dashboard Rincian Pengeluaran

Dashboard memakai satu queryset `OperationalExpense` pada siklus terpilih sebagai sumber tunggal.

- Penggajian: kategori `Tenaga Kerja`.
- Penyusutan: kategori `Penyusutan`.
- Administrasi: kategori `Administrasi`.
- Biaya Produksi & Operasional: total dikurangi tiga kategori di atas.
- Total Pengeluaran: seluruh `OperationalExpense`, sehingga gaji tidak dijumlahkan dua kali.
- Laba/Rugi: Total Omzet dikurangi Total Pengeluaran.

Tidak ada perubahan model atau migration database.
