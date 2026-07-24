#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/var/www/uen/smart_shrimp_farm}"
MIG_DIR="$PROJECT_DIR/chat_ai/migrations"
BACKUP_DIR="$PROJECT_DIR/migration_backup_$(date +%Y%m%d_%H%M%S)"

if [ ! -d "$MIG_DIR" ]; then
  echo "Folder migration tidak ditemukan: $MIG_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

for pattern in '0006_*.py' '0007_merge_*.py'; do
  while IFS= read -r -d '' file; do
    echo "Memindahkan migration sisa: $file"
    mv "$file" "$BACKUP_DIR/"
  done < <(find "$MIG_DIR" -maxdepth 1 -type f -name "$pattern" -print0)
done

find "$MIG_DIR/__pycache__" -type f \( -name '0006*.pyc' -o -name '0007*.pyc' \) -delete 2>/dev/null || true

echo "Migration chat_ai yang tersedia:"
find "$MIG_DIR" -maxdepth 1 -type f -name '*.py' -printf '%f\n' | sort

echo
echo "Selanjutnya jalankan:"
echo "  source $PROJECT_DIR/env/bin/activate"
echo "  cd $PROJECT_DIR"
echo "  python manage.py showmigrations chat_ai"
echo "  python manage.py check"
echo "  python manage.py migrate"
