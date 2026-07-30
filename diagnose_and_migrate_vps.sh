#!/usr/bin/env bash
set -uo pipefail

PROJECT_DIR="${1:-/var/www/uen/smart_shrimp_farm}"
cd "$PROJECT_DIR" || { echo "ERROR: folder proyek tidak ditemukan: $PROJECT_DIR"; exit 1; }

if [ -x "$PROJECT_DIR/env/bin/python" ]; then
  PY="$PROJECT_DIR/env/bin/python"
elif command -v python >/dev/null 2>&1; then
  PY="$(command -v python)"
else
  echo "ERROR: Python tidak ditemukan. Aktifkan virtualenv terlebih dahulu."
  exit 1
fi

LOG="$PROJECT_DIR/migrate_vps_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== Smart Shrimp Farm - diagnosis migrasi VPS ==="
echo "Waktu       : $(date -Is)"
echo "Project     : $PROJECT_DIR"
echo "Python      : $PY"
"$PY" -V

echo
echo "[1/8] Memastikan file payroll tersedia"
for f in payroll/__init__.py payroll/apps.py payroll/models.py payroll/migrations/0001_initial.py smart_shrimp_farm/settings.py; do
  test -f "$f" || { echo "ERROR: file tidak ditemukan: $f"; exit 1; }
done

echo
echo "[2/8] Memastikan payroll terdaftar pada settings aktif"
"$PY" - <<'PY'
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'smart_shrimp_farm.settings'
from django.conf import settings
print('DJANGO_SETTINGS_MODULE =', os.environ['DJANGO_SETTINGS_MODULE'])
print('Payroll entries        =', [x for x in settings.INSTALLED_APPS if 'payroll' in x.lower()])
assert 'payroll.apps.PayrollConfig' in settings.INSTALLED_APPS, (
    "payroll.apps.PayrollConfig belum ada pada INSTALLED_APPS settings aktif"
)
print('Database engine        =', settings.DATABASES['default']['ENGINE'])
print('Database host          =', settings.DATABASES['default'].get('HOST') or '(local/sqlite)')
print('Database name          =', settings.DATABASES['default'].get('NAME'))
PY
STATUS=$?; [ $STATUS -eq 0 ] || { echo "GAGAL pada pemeriksaan settings."; exit $STATUS; }

echo
echo "[3/8] Memeriksa driver database"
"$PY" - <<'PY'
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'smart_shrimp_farm.settings'
from django.conf import settings
engine = settings.DATABASES['default']['ENGINE']
if engine.endswith('postgresql'):
    try:
        import psycopg2
        print('psycopg2 tersedia:', psycopg2.__version__)
    except Exception as exc:
        raise SystemExit(
            'ERROR: VPS memakai PostgreSQL tetapi psycopg2 belum tersedia. '
            'Jalankan: env/bin/pip install psycopg2-binary==2.9.10\nDetail: ' + repr(exc)
        )
else:
    print('Driver PostgreSQL tidak diperlukan untuk backend:', engine)
PY
STATUS=$?; [ $STATUS -eq 0 ] || exit $STATUS

echo
echo "[4/8] Memeriksa sintaks dan import Django"
"$PY" -m compileall -q payroll smart_shrimp_farm finance || exit $?
"$PY" manage.py check --traceback || exit $?

echo
echo "[5/8] Memeriksa koneksi database"
"$PY" manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Database connection: OK')" || exit $?

echo
echo "[6/8] Status migration payroll dan finance"
"$PY" manage.py showmigrations finance payroll --plan || exit $?

echo
echo "[7/8] Menjalankan seluruh migration"
"$PY" manage.py migrate --noinput --traceback || exit $?

echo
echo "[8/8] Pemeriksaan akhir"
"$PY" manage.py check --deploy --fail-level ERROR || exit $?

echo
echo "BERHASIL: migrasi selesai. Log tersimpan di: $LOG"
echo "Selanjutnya restart Gunicorn, lalu cek: sudo journalctl -u gunicorn -n 100 --no-pager"
