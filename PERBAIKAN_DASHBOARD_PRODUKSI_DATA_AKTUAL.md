# Perbaikan Dashboard Produksi Data Aktual

Dashboard produksi sekarang membaca data berdasarkan siklus terpilih dan tetap menyertakan data lama dengan `cycle=NULL` selama masa transisi.

Prioritas sumber populasi tebar:
1. Modul Stocking/Data Tebar.
2. Fallback nilai `stocking_count` dari sampling terbaru per kolam.

Prioritas sumber pakan:
1. Cek Anco.
2. Data Harian Kolam.
3. Log Pakan.
4. Parameter Harian.
5. Sampling.

Jika data hari ini belum ada, dashboard menampilkan data pakan terbaru berikut tanggal dan sumbernya, bukan memaksa angka nol.

KPI ABW, FCR, biomassa, DOC, pakan per kolam, alert anco, dan mortalitas dihitung dari data terbaru pada siklus terpilih.
