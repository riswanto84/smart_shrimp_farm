# Perbaikan Dashboard FR dan Index

Perubahan:

1. Status Ollama dipindahkan ke topbar kanan dan tidak lagi berbentuk card.
2. Card Omzet Siklus pada bagian Realisasi Panen Riil dihapus.
3. Card estimasi biomassa dibedakan secara tegas menjadi:
   - Estimasi Sisa Udang di Kolam (FR)
   - Estimasi Sisa Udang (Index)
4. Card FR menggunakan `production_total_kg`, yang bersumber dari biomassa FR sampling terakhir, dikurangi panen parsial dan biomassa mortalitas setelah sampling.
5. Card Index menggunakan `production_index_total_kg` dengan pengurangan panen parsial dan biomassa mortalitas setelah sampling.
6. Kolam yang selesai panen tetap tidak dimasukkan dalam estimasi sisa biomassa.

Tidak ada perubahan model maupun migration database.
