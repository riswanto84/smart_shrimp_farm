# Sinkronisasi Status Pembayaran

Perubahan:
- Saldo Piutang Usaha menjadi sumber kebenaran status pembayaran.
- Saldo piutang <= 0 otomatis membuat Nota Penjualan berstatus `Lunas`.
- Saldo piutang > 0 otomatis membuat Nota Penjualan berstatus `Belum Lunas`.
- Fungsi `sync_sale_receivable()` selalu menyinkronkan `Sale.status`.
- Ditambahkan command untuk memperbaiki data lama:

    python manage.py sync_payment_statuses

- Tidak ada perubahan model atau migration.
- Tidak perlu menjalankan makemigrations atau migrate.
