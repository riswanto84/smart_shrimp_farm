# Perbaikan Warna Weather Card

Weather Card dengan status `live` maupun `cache` sekarang menggunakan tema biru yang sama.
Status `offline` saja yang menggunakan warna abu-abu. Label "Data terakhir tersimpan" tetap ditampilkan untuk membedakan data cache dari data API langsung.

Tidak ada perubahan database. Setelah pemasangan jalankan `collectstatic`, restart service Django/Gunicorn dan Nginx, lalu hard refresh browser.
