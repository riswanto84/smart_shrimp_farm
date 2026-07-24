# Perbaikan Migration Chat AI dan Ledger

Masalah VPS:

`chat_ai.0008_merge_20260724_1046` merujuk migration lama
`chat_ai.0007_merge_20260724_0652` yang tidak ada pada source terbaru.

Paket ini menambahkan migration kompatibilitas:

`chat_ai/migrations/0007_merge_20260724_0652.py`

Migration tersebut tidak mengubah tabel. Fungsinya hanya menyambungkan graph
migration lama VPS ke migration streaming terbaru:

`0007_alter_chatmessage_message_alter_chatsession_title`

## Pemasangan

Backup database dan source terlebih dahulu, lalu ekstrak paket ke direktori
project. Jangan menghapus migration `0008_merge_20260724_1046.py` yang sudah ada
di VPS.

Jalankan:

```bash
cd /var/www/uen/smart_shrimp_farm
chmod +x repair_migrations.sh
./repair_migrations.sh
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```

Atau secara manual:

```bash
source env/bin/activate
python manage.py showmigrations chat_ai
python manage.py showmigrations finance
python manage.py migrate
python manage.py rebuild_ledger
python manage.py check
```

Tidak perlu menjalankan `makemigrations` sebelum graph migration kembali sehat.
