# Ledger Double Entry

Perubahan:
- Model LedgerAccount, JournalEntry, JournalLine.
- Jurnal sistem berpasangan.
- Bagan akun standar.
- Neraca bersumber dari ledger.
- Neraca Saldo dan Buku Besar.
- Akun `Selisih Saldo Awal` ditampilkan transparan; bukan disembunyikan.
- Command sinkronisasi: `python manage.py rebuild_ledger`.

## Instalasi
```bash
source env/bin/activate
python manage.py migrate finance
python manage.py rebuild_ledger
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```

Migration baru: `0012_ledger_double_entry.py`.
