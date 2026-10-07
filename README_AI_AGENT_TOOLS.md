# Smart Shrimp AI Agent — Database Tools

Versi ini menambahkan **read-only AI Tools + Ollama Tool Calling** ke modul `chat_ai`.

## Arsitektur

`User -> Django chat_ai -> Ollama -> AI Tool -> Django ORM -> Database -> Ollama -> jawaban`

Ollama **tidak** menerima credential database dan **tidak** menjalankan SQL. Semua query dilakukan oleh fungsi Python yang sudah di-whitelist.

## Tools

- `get_active_cycle`
- `get_pond_overview`
- `get_stocking_data`
- `get_water_quality`
- `get_feed_history`
- `get_anco_history`
- `get_sampling_history`
- `get_siphon_history`
- `get_treatment_history`
- `get_harvest_history`
- `get_production_summary`
- `get_financial_summary`
- `get_receivables_payables`

## Aturan scope

- Siklus yang dipilih pada UI menjadi scope utama.
- Jika kolam dipilih pada chat, tool tidak boleh berpindah ke kolam lain.
- Jika tidak ada kolam yang dipilih, tool produksi dapat mengambil seluruh kolam dalam siklus.
- Tool hanya membaca database.
- Tidak ada tool INSERT/UPDATE/DELETE.

## Pakan

Untuk histori pakan, sumber diprioritaskan:

1. `operations.AncoCheck.daily_feed_kg` — P/H lapangan.
2. `operations.FeedLog.quantity_kg`.
3. `operations.DailyPondRecord.daily_feed_kg`.

Ini menghindari kondisi ketika `DailyPondRecord` kosong tetapi data pakan sebenarnya tersimpan di Cek Anco.

## Keuangan

`get_financial_summary` memakai `finance.services.profit_loss.calculate_profit_loss`, yaitu mesin P&L otoritatif aplikasi. Dengan demikian angka AI mengikuti aturan laba/rugi aplikasi, termasuk penyusutan.

## Model Ollama

Gunakan model Ollama yang mendukung tool calling. Untuk server RTX 3060, disarankan model 7B/8B yang mendukung tool calling, misalnya Qwen 2.5 7B atau model setara.

Contoh `.env`:

```env
OLLAMA_URL=http://IP_TAILSCALE_SERVER:11434
OLLAMA_MODEL=qwen2.5:7b
```

Jika Ollama berada di mesin yang sama:

```env
OLLAMA_URL=http://127.0.0.1:11434
```

## Pengujian

1. Pastikan Ollama hidup dan model sudah di-pull.
2. Jalankan Django.
3. Pilih siklus dan, bila perlu, kolam pada halaman Chat AI.
4. Tanyakan contoh:
   - `Bagaimana kondisi Kolam 3 saat ini?`
   - `Tampilkan histori DO dan pH Kolam 3 14 hari terakhir.`
   - `Berapa total pakan Kolam 3 30 hari terakhir?`
   - `Analisa tren ABW, ADG, FCR, SR dan biomass Kolam 3.`
   - `Berapa laba siklus ini dan berapa utang/piutang yang masih outstanding?`

## Catatan

ZIP ini tidak mengubah schema database, sehingga **tidak membutuhkan migration baru** untuk fitur AI Agent.
