# Export Database SQL — SMART SHRIMP FARM

Fitur ini menyediakan **Export Database SQL** khusus Owner/Root.

## Auto-detect `pg_dump`
Untuk PostgreSQL, aplikasi otomatis mencari executable `pg_dump` pada:

1. `PG_DUMP_PATH` jika diset
2. `PATH` sistem (`shutil.which`)
3. `venv/bin/pg_dump` dan `.venv/bin/pg_dump`
4. `/usr/bin/pg_dump`
5. `/usr/local/bin/pg_dump`
6. `/usr/local/pgsql/bin/pg_dump`
7. `/opt/postgresql/bin/pg_dump`
8. `/usr/lib/postgresql/*/bin/pg_dump` dan lokasi PostgreSQL versioned lain; versi terbaru diprioritaskan

Ini penting pada server Gunicorn/systemd karena PATH service sering berbeda dengan PATH saat login SSH.

Jika lokasi `pg_dump` khusus, dapat ditentukan melalui environment variable:

```bash
PG_DUMP_PATH=/usr/lib/postgresql/16/bin/pg_dump
```

## Akses
- Hanya pengguna Owner/Owner Tambak atau Django superuser yang dapat menjalankan export.
- Menu muncul di bagian **PENGATURAN**.
- Setiap export dicatat pada **Log Aktivitas** dengan action type `export`.

## Database yang didukung
### PostgreSQL
Menggunakan `pg_dump` dan menghasilkan SQL berisi schema + data. Export dibuat tanpa ownership/ACL (`--no-owner --no-privileges`) agar lebih mudah direstore pada server lain.

### SQLite
Menggunakan `iterdump()` bawaan SQLite untuk menghasilkan SQL schema + data.

## URL
Endpoint internal:

`/accounts/database/export-sql/`

Nama file otomatis menggunakan timestamp, contoh:

`smart_shrimp_farm_backup_20260831_072500.sql`

## Catatan keamanan
Backup database berisi data aplikasi secara keseluruhan. Jangan membagikan file SQL ke pihak yang tidak berwenang dan simpan backup di lokasi yang aman.
