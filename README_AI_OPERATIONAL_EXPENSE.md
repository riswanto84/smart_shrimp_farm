# AI OperationalExpense

Fitur ini menambahkan input Pengeluaran Operasional berbantuan AI ke Smart Shrimp Farm.

## Alur
1. Buka **Keuangan & Pajak → Pengeluaran Operasional**.
2. Klik **AI Input Pengeluaran**.
3. Pilih bukti PDF/JPG/JPEG/PNG/WEBP (maks. 10 MB).
4. Opsional berikan instruksi, misalnya `Ini untuk Kolam 3`.
5. AI membaca bukti menggunakan Ollama dan menghasilkan draft.
6. Periksa hasilnya.
7. Klik **Setujui & Posting Pengeluaran**.
8. Sistem membuat `OperationalExpense`, menyalin bukti menjadi `ExpenseDocument`, dan menulis audit log.

## Ollama Vision
Model yang dipakai untuk gambar dikonfigurasi dengan:

`OLLAMA_VISION_MODEL=qwen2.5vl:7b`

Jika model tersebut tidak tersedia, instal model vision di server Ollama atau ubah `.env` ke model vision yang memang tersedia di server Anda.

Untuk PDF berbasis teks, sistem menggunakan `pypdf` untuk mengambil teks lalu meminta Ollama menstrukturkannya. PDF hasil scan yang hanya berisi gambar memerlukan model/pipeline OCR atau vision tambahan.

## Keamanan
- AI tidak mendapat akses SQL/database langsung.
- AI hanya membuat `AIAction` berstatus `draft`.
- Posting membutuhkan permission `ai.approve`.
- Bukti sementara disimpan pada `AIOperationalExpenseDocument` sampai action diproses.
- Saat posting, bukti disalin ke `finance.ExpenseDocument`.
- Aktivitas dicatat pada `AIAuditLog` dan `accounts.AuditLog`.
- Field wajib tanggal, kategori, nama, dan nominal harus terbaca sebelum tombol posting tersedia.

## Migration
Jalankan satu kali:

```bash
python manage.py migrate
```

Tidak ada migration pada `finance` untuk fitur ini.
