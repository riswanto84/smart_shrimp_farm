# Perbaikan Pencarian Seluruh Database

Perbaikan ini memastikan tombol **Cari** mengirim parameter `q` ke view Django dan pencarian dilakukan pada QuerySet sebelum pagination.

## Perubahan
- Menghapus perilaku pencarian JavaScript yang hanya menyaring 10 baris pada halaman aktif.
- Form pencarian menggunakan metode GET dan mempertahankan filter tanggal, kategori, kolam, serta filter lain.
- Parameter halaman dihapus ketika pencarian baru dijalankan.
- Cache-busting ditambahkan pada `global_data_search.js` agar browser tidak terus memakai file JavaScript lama.
- Pengeluaran Operasional mencari langsung pada kategori, nama pengeluaran, metode, catatan, nomor dokumen, dan nama kolam.
- Ringkasan, total, ekspor, dan pagination Pengeluaran Operasional memakai hasil pencarian yang sama.
- Halaman lain yang menggunakan `paginate_queryset` tetap mencari QuerySet sebelum pagination.

## Deployment VPS
Setelah mengganti file, jalankan:

```bash
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Kemudian lakukan hard refresh browser: `Ctrl+Shift+R` atau `Cmd+Shift+R`.
