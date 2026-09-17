# Perbaikan Ringkasan FCR dan ADG

Kartu ringkasan pada halaman **Data Sampling** kini menggunakan satu data sampling terakhir dari setiap kolam:

- **Rata-rata ABW**: rata-rata ABW Today dari sampling terakhir per kolam.
- **Rata-rata ADG**: rata-rata ADG Weekly/Actual (`adg_weekly`) dari sampling terakhir per kolam.
- **Rata-rata FCR**: rata-rata FCR dari sampling terakhir per kolam.
- **Biomassa FR**: jumlah Biomassa FR dari sampling terakhir per kolam.

Pemilihan data terakhir diurutkan berdasarkan tanggal terbaru, kemudian ID/PK terbaru bila terdapat lebih dari satu data pada tanggal yang sama. Query tetap mengikuti filter tanggal, kolam, dan siklus yang sedang diterapkan pada halaman.
