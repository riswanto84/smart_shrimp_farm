#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source env/bin/activate
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
printf '\nPerbaikan grafik berhasil diterapkan. Lakukan hard refresh browser.\n'
