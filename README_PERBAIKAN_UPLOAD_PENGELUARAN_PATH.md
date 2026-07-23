# Perbaikan Upload Dokumen Pengeluaran Operasional

## Error yang diperbaiki

`NameError: name 'Path' is not defined` pada URL edit pengeluaran ketika pengguna mengunggah dokumen.

## Perubahan

- Memindahkan impor `Path` dari `pathlib` ke bagian atas `finance/views.py`.
- Memindahkan impor Django `messages` ke bagian atas sehingga tersedia untuk seluruh fungsi upload.
- Membersihkan komponen folder dari nama file menggunakan `Path(uploaded_file.name).name`.
- Mempertahankan validasi ekstensi dokumen dan batas maksimal 10 MB per file.
- Berlaku pada upload ketika menambah maupun mengedit pengeluaran operasional.

Tidak ada perubahan model dan tidak diperlukan migrasi database.
