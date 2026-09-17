# Fix NameError Sinkronisasi Status

Perbaikan:
- Menghapus seluruh referensi `_sync_sale_payment_status`.
- Menghapus helper lama yang tidak konsisten.
- Menyatukan logika status langsung di `sync_sale_receivable`.
- Memastikan `Decimal` hanya diimpor pada level modul.
- Menghapus `finance/signals.py` yang salah.
- Tidak ada perubahan model atau migration.

Setelah deploy:
1. python manage.py check
2. python manage.py sync_payment_statuses
3. restart service
