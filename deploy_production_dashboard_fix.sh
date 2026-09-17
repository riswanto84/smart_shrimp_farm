#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source env/bin/activate

echo "[1/5] Verifikasi file dashboard terbaru"
grep -q "Total Panen Riil" templates/operations/production_dashboard.html
grep -q "2026.08.02-harvest-size30-v2" operations/views.py

echo "[2/5] Django system check"
python manage.py check

echo "[3/5] Collect static"
python manage.py collectstatic --noinput

echo "[4/5] Bersihkan cache Python"
find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete 2>/dev/null || true

echo "[5/5] Restart layanan"
sudo systemctl restart gunicorn
sudo systemctl reload nginx

echo "SELESAI. Buka Dashboard Produksi dan pastikan terlihat: Build 2026.08.02-harvest-size30-v2"
