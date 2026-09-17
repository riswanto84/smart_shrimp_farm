# Perbaikan Migration `chat_ai`

Paket ini dibangun ulang tanpa migration AI yang rusak. Rantai migration yang valid adalah:

- `0001_initial`
- `0002_chat_retention`
- `0003_add_cycle`
- `0004_backfill_legacy_cycle_data`
- `0005_alter_chatmessage_role`

Tidak ada dependency ke `0006_chatattachment_chatmessage_is_complete` maupun `0007_merge_20260724_0652`.

## Penting saat memasang di VPS

Mengekstrak ZIP di atas folder lama tidak otomatis menghapus file yang sudah ada. Karena itu, file `0007_merge_20260724_0652.py` yang tersisa di VPS harus dihapus atau dipindahkan terlebih dahulu.

Jalankan:

```bash
cd /var/www/uen/smart_shrimp_farm
chmod +x repair_chat_ai_migrations.sh
./repair_chat_ai_migrations.sh /var/www/uen/smart_shrimp_farm
```

Lalu:

```bash
source env/bin/activate
python manage.py showmigrations chat_ai
python manage.py check
python manage.py migrate
sudo systemctl restart smartshrimp
```

Untuk paket ini tidak perlu menjalankan `makemigrations`, karena perubahan koreksi Modal Pemilik tidak mengubah model database.

## Jangan lakukan

Jangan menjalankan `migrate --fake` dan jangan menghapus tabel `chat_ai`, karena masalahnya hanya file migration sisa yang dependency-nya tidak tersedia.
