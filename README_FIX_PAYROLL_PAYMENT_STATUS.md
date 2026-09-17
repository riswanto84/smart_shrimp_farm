# Perbaikan payroll -> pengeluaran operasional

Error yang diperbaiki:

`null value in column "payment_status" of relation "finance_operationalexpense" violates not-null constraint`

Database produksi masih mempunyai kolom legacy `payment_status` yang wajib diisi,
sementara model Django saat ini tidak lagi memetakan kolom tersebut. Migration
`finance.0012_operationalexpense_payment_status_default` memberikan default
`paid` pada level PostgreSQL sehingga transaksi payroll yang lunas dapat kembali
membuat Pengeluaran Operasional tanpa error.

Jalankan:

```bash
python manage.py migrate finance
python manage.py migrate
```
