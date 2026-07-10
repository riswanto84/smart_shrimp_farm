# Akses Siklus Budidaya

Fitur Siklus Budidaya hanya dapat diakses oleh:

- Superuser Django
- Role `Owner`
- Role `Owner Tambak`

Role lain, termasuk Admin, Teknisi, Kasir, Akuntan, dan Investor, tidak dapat membuka URL `/cycles/`, menambah, mengedit, atau mengganti siklus aktif. Menu dan pemilih siklus juga disembunyikan.
