# Smart Shrimp Farm - Enterprise Cycle Update

Fitur: dashboard dan laporan per siklus, owner-only, ekspor PDF/Excel, tombol ikon profesional, status Ollama real-time, data aktual tanpa dummy, dan integrasi cycle.

## Instalasi
```bash
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py backfill_cycle_data
python manage.py collectstatic --noinput
```

Buat `.env` dari `.env.example`. Untuk localhost tanpa PostgreSQL, set `DB_ENGINE=django.db.backends.sqlite3` dan `DB_NAME=/path/db.sqlite3`.
