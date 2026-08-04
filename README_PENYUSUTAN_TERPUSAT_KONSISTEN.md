# Perbaikan Penyusutan Terpusat

Semua modul keuangan kini memakai `finance/services/depreciation.py` sebagai satu sumber perhitungan garis lurus.

- Dashboard menampilkan penyusutan tahun berjalan yang sama dengan laporan Penyusutan Fiskal.
- Laba/Rugi mengabaikan posting `OperationalExpense` kategori Penyusutan lama agar tidak terjadi duplikasi.
- Penyusutan dihitung otomatis dari register aset dan ditambahkan satu kali ke beban.
- Neraca, PDF, dan laporan penyusutan memakai engine yang sama.
- Tidak ada migration database baru.
