# Multiple File Bukti Pengeluaran Operasional

## Perubahan
- Satu pengeluaran dapat menyimpan maksimal 20 lampiran.
- Maksimal ukuran 10 MB per file.
- Format: PDF, JPG/JPEG, PNG, WEBP, DOCX, XLSX.
- Lampiran lama dimigrasikan otomatis ke tabel lampiran baru.
- File baru dapat ditambahkan saat edit.
- Lampiran dapat dihapus satu per satu tanpa menghapus transaksi pengeluaran.
- Daftar pengeluaran menampilkan jumlah lampiran dan menu untuk membuka setiap file.

## Instalasi di VPS
```bash
source env/bin/activate
python manage.py migrate finance
python manage.py check
sudo systemctl restart smartshrimp
sudo systemctl reload nginx
```

Pastikan konfigurasi `MEDIA_ROOT`, `MEDIA_URL`, dan Nginx untuk `/media/` sudah aktif.
