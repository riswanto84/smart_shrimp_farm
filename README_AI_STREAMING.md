# Smart Shrimp AI — Streaming Ollama

Fitur yang ditambahkan:
- Streaming token melalui `StreamingHttpResponse` dan format SSE.
- Tombol Stop, auto-scroll, Enter untuk mengirim, Shift+Enter untuk baris baru.
- Konteks kolam dan 12 pesan terakhir.
- Penyimpanan pertanyaan dan jawaban final ke riwayat yang sudah ada.
- Fallback AI Gateway ke Ollama langsung.

## Konfigurasi `.env`
```env
OLLAMA_URL=http://IP_TAILSCALE_OLLAMA:11434
OLLAMA_MODEL=gemma2:2b
OLLAMA_CONNECT_TIMEOUT=10
OLLAMA_READ_TIMEOUT=300
```

## Nginx
Tambahkan blok ini sebelum `location /` dan sesuaikan socket:
```nginx
location /chat-ai/stream/ {
    proxy_pass http://unix:/var/www/uen/smart_shrimp_farm/smartshrimp.sock;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
    gzip off;
}
```

## Gunicorn
Pastikan timeout cukup panjang, contoh `--timeout 600`, kemudian restart service.

## Instalasi
```bash
source env/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart smartshrimp
sudo nginx -t && sudo systemctl reload nginx
```
Tidak ada migrasi baru untuk fitur streaming ini.
