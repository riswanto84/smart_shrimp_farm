# Perbaikan Dashboard Produksi — Data Aktual

Perbaikan ini memastikan KPI Dashboard Produksi membaca data sebenarnya pada siklus terpilih:

- Populasi tebar diprioritaskan dari `Stocking`; bila belum ada, memakai jumlah tebar dari sampling terbaru per kolam.
- Pakan dibaca dari Cek Anco, Data Harian, atau Parameter Harian. Bila hari ini belum ada input, dashboard menampilkan pakan pada tanggal data terakhir dengan label **Pakan Terbaru**.
- ABW dan FCR dihitung dari sampling terbaru masing-masing kolam, bukan rata-rata seluruh histori.
- Mortalitas memakai rentang 7 hari yang berakhir pada data siphon terbaru.
- Alert anco memakai rentang 3 hari yang berakhir pada data anco terbaru.
- Semua queryset mengikuti siklus terpilih dan tetap membaca data lama yang belum memiliki siklus selama masa transisi.
- Ringkasan alur produksi menampilkan angka aktual, bukan hanya teks statis.
