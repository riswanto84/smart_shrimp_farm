#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [[ -f env/bin/activate ]]; then
  # shellcheck disable=SC1091
  source env/bin/activate
elif [[ -f venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

find chat_ai finance -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find chat_ai finance -type f -name '*.pyc' -delete 2>/dev/null || true

python manage.py showmigrations chat_ai
python manage.py showmigrations finance
python manage.py migrate
python manage.py rebuild_ledger
python manage.py check

echo "Migration graph, ledger, dan pemeriksaan Django selesai."
