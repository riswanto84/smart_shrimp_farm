# Perbaikan Konsistensi Data Sampling Final

Perubahan utama:

- ABW disimpan 2 desimal, tetapi semua perhitungan turunan memakai ABW presisi penuh (`berat / jumlah`).
- Size dihitung dari ABW presisi penuh.
- Populasi FR dihitung dari Biomassa FR × Size presisi penuh.
- Biomassa Index dihitung dari Populasi Index × ABW presisi / 1000.
- FCR dihitung sesuai Excel: Pakan Kumulatif / Biomassa Index.
- Kartu Rata-rata FCR memakai batch sampling terakhir dan rumus yang sama.
- Form input sampling menampilkan FCR dengan rumus Biomassa Index.

Contoh Kolam 7:

- ABW presisi = 1002 / 125 = 8,016 g
- Size = 1000 / 8,016 = 124,75
- Biomassa Index = 160000 × 8,016 / 1000 = 1.282,56 kg
- FCR = 1.335,4 / 1.282,56 = 1,04
