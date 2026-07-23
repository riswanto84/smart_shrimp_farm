# Smart Shrimp AI Streaming

Fitur baru:
- Streaming respons Ollama token demi token melalui Django `StreamingHttpResponse`.
- Tombol hentikan generasi.
- Multi percakapan: buat, buka, ubah judul, tandai penting, dan hapus.
- Upload maksimal 5 file per pesan.
- Ekstraksi TXT, Markdown, CSV, JSON, PDF, DOCX, dan XLSX.
- Dukungan PNG/JPG/WEBP untuk model Ollama vision seperti `llava` atau `qwen2.5vl`.
- Konteks data kolam dan riwayat 20 pesan terakhir.
- Tampilan respons markdown sederhana dan layout responsif.

## Instalasi

```bash
cd smart_shrimp_farm
source env/bin/activate   # sesuaikan nama virtualenv
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8001
```

`.env` minimum:

```env
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
CHAT_AI_MAX_UPLOAD_MB=15
CHAT_AI_MAX_EXTRACTED_CHARS=50000
```

Untuk gambar gunakan model vision dan ubah `OLLAMA_MODEL`, misalnya model vision yang sudah tersedia pada instalasi Ollama Anda.

## Nginx produksi

Pada location yang meneruskan ke Gunicorn, streaming memerlukan buffering dimatikan:

```nginx
location / {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
}
```

Gunicorn disarankan:

```bash
gunicorn smart_shrimp_farm.wsgi:application --bind 127.0.0.1:8001 --workers 3 --threads 4 --timeout 600
```
