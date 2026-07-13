# Perbaikan Dashboard Estimasi Panen Size 30

Dashboard Ringkasan Kolam sekarang menampilkan estimasi tanggal tercapainya size 30 berdasarkan data sampling terakhir pada siklus aktif.

Rumus:
- ABW target size 30 = 1000 / 30 = 33,33 gram/ekor
- Sisa hari = ceil((33,33 - ABW Today) / ADG Actual)
- Tanggal estimasi = tanggal sampling terakhir + sisa hari

Ketentuan:
- ABW dan ADG memakai sampling terakhir pada batch/tanggal terbaru.
- ADG Actual memakai field `adg_weekly` (gram/hari).
- Jika ADG belum tersedia atau nol, dashboard menampilkan bahwa estimasi belum dapat dihitung.
- Jika ABW sudah >= 33,33 gram, target size 30 dianggap telah tercapai.
- DOC pada Ringkasan Kolam juga memakai DOC riil dari sampling terakhir, bukan angka dummy.
