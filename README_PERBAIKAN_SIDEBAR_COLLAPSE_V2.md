# Perbaikan Sidebar Collapse/Expand V2

- Desktop (>820 px): tombol hamburger menciutkan sidebar menjadi 78 px dan memperlebar area utama.
- Klik kembali mengembalikan sidebar penuh.
- Status disimpan pada localStorage.
- Mobile tetap memakai sidebar overlay.
- Grafik menerima event resize setelah transisi.
- Cache CSS dinaikkan ke `20260729-sidebar-collapse-v2`.

Setelah deploy jalankan `python manage.py collectstatic --noinput`, restart Gunicorn, lalu hard refresh browser.
