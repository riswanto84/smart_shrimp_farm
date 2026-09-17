# Perbaikan IntegrityError Saat Menghapus Pengeluaran

## Masalah

Pada database PostgreSQL produksi masih terdapat tabel legacy:

`finance_operationalexpenseattachment`

Tabel tersebut masih memiliki foreign key ke `finance_operationalexpense`, sehingga penghapusan pengeluaran dapat gagal dengan:

`violates foreign key constraint ... finance_operationale_expense_id_...`

## Perbaikan

1. `finance.views.delete_expense` sekarang berjalan dalam transaksi.
2. Sebelum menghapus `OperationalExpense`, sistem mendeteksi tabel legacy tersebut secara aman.
3. Jika tabel ada, semua attachment legacy yang terkait dengan pengeluaran dihapus terlebih dahulu.
4. Django kemudian menghapus `ExpenseDocument` modern melalui `CASCADE`.
5. Migration `0016_legacy_expense_attachment_cascade.py` mengubah foreign key legacy PostgreSQL menjadi `ON DELETE CASCADE`, sehingga penghapusan berikutnya juga aman walaupun dilakukan dari ORM/database.

## Deploy

Di server:

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
unzip -o smart_shrimp_farm_delete_expense_fix.zip -d /tmp/ssf_fix
```

Salin isi project hasil ZIP ke project produksi sesuai prosedur deployment Anda, kemudian:

```bash
python manage.py migrate
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart smartshrimp
```

Jika nama service Gunicorn berbeda, restart service Gunicorn yang digunakan Smart Shrimp Farm.

## Catatan

Migration hanya mengubah constraint pada PostgreSQL jika tabel legacy memang ada. Instalasi baru yang tidak memiliki tabel legacy tidak terpengaruh.
