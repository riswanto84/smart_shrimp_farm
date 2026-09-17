# Perbaikan IntegrityError supplier_name

## Masalah
Database PostgreSQL produksi masih mempunyai kolom lama
`finance_operationalexpense.supplier_name` dengan aturan `NOT NULL`, sedangkan
model Django saat ini tidak lagi memiliki field tersebut. Saat pengeluaran baru
disimpan, ORM tidak menyertakan kolom itu sehingga PostgreSQL menolak INSERT.

## Perbaikan
Migration `finance.0014_operationalexpense_supplier_name_default`:

- mendeteksi kolom lama hanya jika benar-benar tersedia;
- mengisi baris lama yang masih `NULL` dengan string kosong;
- menetapkan default database string kosong;
- mempertahankan `NOT NULL`;
- tidak menambah field supplier ke form dan tidak mengubah data pengeluaran lain.

## Deployment VPS

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
python manage.py migrate finance
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Hasil migration yang diharapkan:

```text
Applying finance.0014_operationalexpense_supplier_name_default... OK
```
