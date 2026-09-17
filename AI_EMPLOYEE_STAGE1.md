# AI Employee Finance/Payroll — Tahap 1

Modul ini menambahkan AI Employee di `/ai-employee/`. Tahap 1 mendukung:

- membaca payroll terakhir seorang pegawai;
- membaca saldo kasbon;
- membuat draft kasbon melalui bahasa natural;
- approval/reject draft;
- menyimpan `AIAction` dan `AIAuditLog`;
- meneruskan event penting ke `accounts.AuditLog`.

## Contoh perintah

- `Kasbon Budi Rp500.000 untuk operasional tambak`
- `Berapa saldo kasbon Budi?`
- `Berapa gaji Budi terakhir?`

## Aturan keamanan

AI tidak diberi akses SQL/database langsung. Kasbon selalu dibuat sebagai draft. Posting membutuhkan permission `ai.approve`.

## Instalasi

```bash
python manage.py makemigrations ai_employee
python manage.py migrate
python manage.py check
```

Jika deployment memakai Ollama, tidak ada dependensi baru selain paket yang sudah ada karena modul memakai `chat_ai.services.ask_ollama`.
