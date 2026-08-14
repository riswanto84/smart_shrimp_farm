#!/usr/bin/env bash
set -euo pipefail
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
python manage.py collectstatic --noinput
find . -type d -name __pycache__ -prune -exec rm -rf {} +
find . -type f -name '*.pyc' -delete
sudo systemctl restart gunicorn
sudo systemctl reload nginx
echo 'Perbaikan engine penyusutan berhasil diterapkan.'
