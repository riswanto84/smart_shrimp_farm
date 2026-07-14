# Penguncian Siklus Selesai — Final

Perbaikan ini menyatukan sumber siklus terpilih pada context processor dan backend.

Ketika siklus berstatus `completed`/Selesai:
- tombol tambah, edit, hapus, dan import disembunyikan;
- URL langsung untuk tambah/edit/hapus/import ditolak di server;
- detail, filter, template, export Excel, dan PDF tetap tersedia;
- edit/hapus memeriksa siklus milik record, bukan hanya siklus pada session;
- seluruh modul operasional mengikuti pilihan siklus yang sama.

Modul yang dikunci: Parameter Harian, Data Harian Kolam, Cek Anco, Sampling, Siphon, dan Panen.
