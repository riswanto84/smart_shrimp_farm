# Export Database SQL — SMART SHRIMP FARM

Fitur ini menambahkan **Export Database SQL** khusus Owner/Root.

## Akses
- Hanya pengguna yang dikenali sebagai Owner/Owner Tambak atau Django superuser yang dapat menjalankan export.
- Menu muncul di bagian **PENGATURAN**.
- Setiap export dicatat pada **Log Aktivitas** dengan action type `export`.

## Database yang didukung
### PostgreSQL
Menggunakan `pg_dump` dan menghasilkan SQL berisi schema + data. Export dibuat tanpa ownership/ACL (`--no-owner --no-privileges`) agar lebih mudah direstore pada server lain.

Pastikan PostgreSQL client terpasang sehingga command berikut tersedia:

```bash
pg_dump --version
```

### SQLite
Menggunakan `iterdump()` bawaan SQLite untuk menghasilkan SQL schema + data.

## URL
Endpoint internal:

`/accounts/database/export-sql/`

Nama file otomatis menggunakan timestamp, contoh:

`smart_shrimp_farm_backup_20260831_072500.sql`

## Catatan keamanan
Backup database berisi data aplikasi secara keseluruhan. Jangan membagikan file SQL ke pihak yang tidak berwenang dan simpan backup di lokasi yang aman.
