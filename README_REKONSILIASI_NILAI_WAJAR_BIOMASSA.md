# Perbaikan Rekonsiliasi Nilai Wajar Aset Biologis

Perbaikan ini menghapus penggunaan nilai biomassa sebagai akun otomatis **Saldo awal/modal belum direkonsiliasi**.

Neraca kini memisahkan:

1. Laba/rugi operasional tahun berjalan.
2. Cadangan pengakuan awal aset biologis (baseline).
3. Perubahan nilai wajar aset biologis dibanding baseline/snapshot.
4. Nilai akhir aset biologis pada tanggal laporan.
5. Selisih neraca nyata yang tidak lagi ditutup paksa oleh akun penyeimbang.

## Deployment

```bash
python manage.py migrate finance
python manage.py initialize_biological_valuation --date 2026-08-01
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Perintah `initialize_biological_valuation` dijalankan satu kali setelah deployment untuk mengunci baseline. Untuk penutupan periode berikutnya:

```bash
python manage.py initialize_biological_valuation --date YYYY-MM-DD
```

Jika snapshot tanggal yang sama perlu diperbaiki:

```bash
python manage.py initialize_biological_valuation --date YYYY-MM-DD --replace
```

Tanpa baseline tersimpan, laporan tetap dapat dibuka tetapi menandai baseline sebagai **sementara**.
