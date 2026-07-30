# Patch Indikator Kesehatan Rasio

Perubahan hanya menyentuh halaman Laporan Neraca:

- Menambahkan badge warna dan interpretasi otomatis untuk Current Ratio, Cash Ratio, Debt to Equity, Debt Ratio, Current Ratio Operasional, dan Coverage Biomassa.
- Warna: hijau, biru, kuning, merah, atau netral sesuai nilai rasio.
- Tidak mengubah model database dan tidak memerlukan migration.

File yang berubah:

1. `finance/views.py`
2. `templates/finance/balance_sheet.html`
