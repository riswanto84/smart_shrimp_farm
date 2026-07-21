# Perbaikan Form Pengeluaran Operasional

Perbaikan ini menangani error `VariableDoesNotExist` pada URL `/finance/expenses/add/`.

## Penyebab
Template menggunakan `default:obj.payment_method`. Pada halaman tambah data, variabel `obj` belum tersedia sehingga Django gagal me-render template.

## Perbaikan
- Pilihan metode pembayaran sekarang memakai `{% firstof %}` dengan nilai default `Cash`.
- View tambah pengeluaran selalu mengirim `obj=None`, `form_data={}`, dan `mode='add'`.
- Multiple file upload tetap aktif.
- Form tambah dan edit telah diuji melalui Django template renderer.

## Pemeriksaan
- `python manage.py check`: tidak ditemukan masalah.
- Template `finance/expense_form.html` berhasil dirender untuk mode tambah.
