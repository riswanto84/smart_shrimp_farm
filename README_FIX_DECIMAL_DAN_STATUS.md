# Perbaikan Decimal dan Status Pembayaran

Perubahan:
- `Decimal` diimpor pada level modul di `finance/receivable_sync.py`.
- Import `Decimal` lokal di dalam fungsi dihapus.
- Menghilangkan `UnboundLocalError`.
- `finance/signals.py` yang salah tetap dihapus.
- `finance/apps.py` tidak lagi memuat signal yang mengimpor model yang tidak ada.
- Status Nota Penjualan:
  - pembayaran >= total nota: Lunas
  - pembayaran < total nota: Belum Lunas
- Command:
  python manage.py sync_payment_statuses
- Tidak ada perubahan model atau migration.
