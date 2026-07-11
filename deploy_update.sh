#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:-/var/www/uen/smart_shrimp_farm}"
cd "$PROJECT_DIR"
if [ -f env/bin/activate ]; then source env/bin/activate; elif [ -f venv/bin/activate ]; then source venv/bin/activate; fi
python3 -m pip install -r requirements.txt
python3 manage.py check
python3 manage.py migrate
python3 manage.py backfill_cycle_data || true
python3 manage.py collectstatic --noinput
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl restart smartshrimp
  sudo systemctl restart nginx
fi
echo "Deploy Smart Shrimp Farm selesai."
