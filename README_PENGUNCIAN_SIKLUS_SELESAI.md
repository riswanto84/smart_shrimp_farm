# Penguncian Siklus Budidaya Selesai

Perubahan:
- Status `Selesai` sekarang mengunci add/edit/delete/import seluruh data operasional.
- Penguncian berlaku di server melalui middleware, bukan hanya tampilan.
- Tombol input, import, edit, dan hapus disembunyikan; detail dan export tetap tersedia.
- Banner arsip muncul pada seluruh halaman ketika siklus selesai dipilih.
- Data operasional secara default difilter ketat berdasarkan siklus; siklus baru tidak menampilkan data lama.
- Saat transisi pertama menjadi selesai, aplikasi menyimpan snapshot KPI akhir dalam `final_snapshot`.
- Notifikasi input harian tidak muncul untuk siklus yang telah selesai.

Setelah deploy wajib menjalankan:

```bash
python manage.py migrate
python manage.py check
```
