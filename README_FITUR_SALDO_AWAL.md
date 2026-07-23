# Fitur Saldo Awal

Menu baru: **Keuangan & Pajak → Saldo Awal**.

Data yang diinput manual:
- Kas Tunai
- Bank BCA, Mandiri, BRI, dan rekening lainnya
- Modal Pemilik
- Laba Ditahan

Data yang tetap dihitung otomatis dan tidak diinput ulang:
- Piutang Usaha
- Utang Usaha
- Aset Tetap
- Akumulasi Penyusutan

Fitur memakai model `BalanceEntry` yang sudah tersedia, sehingga tidak membutuhkan migrasi database baru. Setiap penyimpanan membuat/memperbarui snapshot pada tanggal posisi yang dipilih dan mempertahankan riwayat tanggal sebelumnya.
