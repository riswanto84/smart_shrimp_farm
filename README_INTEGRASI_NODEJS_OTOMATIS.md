# Smart Shrimp Farm + Node.js AI Gateway

ZIP ini sudah berisi source Django dan folder `node_ai_gateway`.

## Cara paling mudah di MacBook

1. Pastikan aplikasi Ollama aktif.
2. Buka folder `node_ai_gateway`.
3. Klik dua kali `install_and_start.command`.
4. Jika macOS memblokir, klik kanan file tersebut → **Open**.
5. Script akan mengecek Node.js/npm, menginstal dependency, membuat token otomatis, dan menjalankan gateway di port 3000.

## Hubungkan Django

Salin API key dari `node_ai_gateway/.env`, kemudian isi `.env` Django:

```env
AI_GATEWAY_URL=http://IP_TAILSCALE_MACBOOK:3000
AI_GATEWAY_API_KEY=TOKEN_DARI_NODE_GATEWAY
AI_GATEWAY_MODEL=llama3.1:8b
OLLAMA_URL=http://IP_TAILSCALE_MACBOOK:11434
OLLAMA_MODEL=llama3.1:8b
```

Untuk pengujian lokal pada MacBook, gunakan:

```env
AI_GATEWAY_URL=http://127.0.0.1:3000
```

Restart Django/Gunicorn setelah mengubah `.env`.

## Perilaku sistem

- Django lebih dahulu memakai Node.js AI Gateway.
- Jika gateway mati, sistem otomatis mencoba Ollama langsung.
- Tidak ada perubahan database dan tidak perlu migrasi khusus untuk integrasi ini.
