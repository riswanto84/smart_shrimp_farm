# Pemisahan Utang Usaha dan Pengeluaran Operasional

- Utang Usaha tetap memakai model `TradeAccount` dan `TradePayment`.
- Pengeluaran Operasional tetap memakai `OperationalExpense`; tidak ada sinkronisasi status otomatis.
- Form Edit Utang Usaha menyediakan status: Belum Lunas, Lunas Sebagian, dan Lunas.
- Nilai pembayaran/status menentukan saldo utang pada Neraca.
- Laba/Rugi tetap mengambil seluruh nilai Pengeluaran Operasional berdasarkan periode (basis akrual), tidak berdasarkan status pembayaran utang.
- Neraca mengambil Utang Usaha dari saldo `original_amount - payments` per tanggal laporan.
- Tidak diperlukan migration database baru.
