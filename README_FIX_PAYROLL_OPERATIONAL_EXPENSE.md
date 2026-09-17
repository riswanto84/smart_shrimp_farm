# Perbaikan Payroll → OperationalExpense

Tanggal: 17 September 2026

## Masalah
`payroll/views.py` mengirim argumen `payment_status` saat membuat/memperbarui
`finance.OperationalExpense`, sementara model `OperationalExpense` tidak memiliki
field tersebut. Ini menyebabkan:

`TypeError: OperationalExpense() got unexpected keyword arguments: 'payment_status'`

## Perbaikan
- Menghapus `payment_status` dari payload `OperationalExpense`.
- Status pembayaran tetap bersumber dari `PayrollRecord.payment_status`.
- Jika payroll yang sebelumnya sudah dibayar diubah menjadi `unpaid`/`partial`,
  expense otomatis yang tertaut akan dihapus agar laporan basis kas tidak menyisakan
  beban gaji yang sudah tidak sesuai.

## Verifikasi
Seluruh file Python proyek berhasil melewati pemeriksaan syntax (`compileall`).
Tidak ada perubahan migration yang diperlukan untuk perbaikan ini.
