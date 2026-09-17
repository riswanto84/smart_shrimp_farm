# Import Excel Operasional

Modul: Cek Anco, Sampling, Siphon, Parameter Harian.

## Akses
Root/Superuser, Owner/Owner Tambak, dan Teknisi.

## Alur
1. Buka daftar modul.
2. Klik **Import Excel**.
3. Upload `.xlsx`.
4. Periksa preview valid/error.
5. Pilih **Perbarui** atau **Lewati duplikat**.
6. Konfirmasi import. Data masuk ke siklus aktif.

## Format lapangan yang didukung
- Siphon: satu tab per kolam (`K1`, `K2`, dst.), header Tanggal/DOC/Mati/Hidup.
- Parameter: satu tanggal untuk banyak kolam; nilai `P/S` dapat berupa `79`, `79/80`, atau `P79 S80`.
- Sampling: blok berulang seperti file `Data Sampling 2.xlsx`; hanya kolom input dasar yang diimpor, rumus turunan dihitung Django.
- Anco: H, S, SS (Sisa Sedikit), dan `-`.
