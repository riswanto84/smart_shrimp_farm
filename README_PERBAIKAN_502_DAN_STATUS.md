# Perbaikan 502 dan Status Pembayaran

Perbaikan:
- Menghapus import `finance.signals` yang menyebabkan Django gagal start.
- Menghapus `finance/signals.py` yang mengimpor model `AccountReceivable` yang tidak ada.
- Mempertahankan sinkronisasi status di fungsi asli `sync_sale_receivable`.
- Status Nota Penjualan dihitung dari total pembayaran aktual pada Sale.
- Menyediakan command aman:
  `python manage.py sync_payment_statuses`
- Tidak ada perubahan model atau migration.

Fungsi sinkronisasi ditemukan di:
finance/receivable_sync.py

Class pada finance.models:
OperationalExpense, ExpenseDocument, OtherRevenue, BalanceEntry, FixedAsset, TradeAccount, TradePayment, TradeDocument
