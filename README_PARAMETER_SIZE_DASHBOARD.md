# Penambahan Parameter Size pada Dashboard Produksi

Perubahan:
- Menambahkan kartu **Size Saat Ini** dalam satuan ekor/kg.
- Menambahkan kartu **Prediksi Size pada target DOC**.
- Menampilkan **Target Size Siklus** dan ekuivalen ABW target.
- Menambahkan kolom Size pada tabel kondisi terbaru per kolam.
- Menambahkan Size pada tooltip grafik perkembangan biomassa.

Rumus:
- Size saat ini = 1.000 / ABW rata-rata sampling terakhir.
- ABW proyeksi = biomassa proyeksi (kg) × 1.000 / populasi hidup.
- Size proyeksi = 1.000 / ABW proyeksi.

Semua nilai mengikuti siklus yang sedang dipilih dan berasal dari data sampling aktual.
