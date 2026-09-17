# Perbaikan Kartu Biomassa FR

Kartu **Biomassa FR** pada menu Data Sampling sekarang dihitung dari satu batch/tanggal sampling terbaru.

Aturan:

1. Tentukan tanggal sampling paling baru dari data yang sudah mengikuti filter dan siklus terpilih.
2. Ambil satu record untuk setiap kolam pada tanggal tersebut.
3. Prioritaskan record yang terikat pada siklus aktif/terpilih dibanding record legacy `cycle=NULL`.
4. Jumlahkan nilai `biomass_kg` (Biomassa FR), bukan Biomassa Index dan bukan seluruh riwayat sampling.

Contoh batch 12/07/2026:

`1.982,18 + 1.921,49 + 1.943,23 + 1.831,28 + 1.485,59 + 1.086,96 = 10.250,72 kg`

Tidak ada perubahan struktur database dan tidak memerlukan migrasi.
