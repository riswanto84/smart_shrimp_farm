# Pembayaran Utang Masuk Beban dan Laba/Rugi (Basis Kas)

Perubahan ini menerapkan kebijakan yang dipilih pengguna:

- Utang usaha belum memengaruhi laba/rugi saat kartu utang dibuat.
- Setiap pembayaran utang otomatis membuat Pengeluaran Operasional pada tanggal pembayaran.
- Pembayaran sebagian mengakui beban sebesar nominal yang dibayar.
- Pelunasan penuh mengakui seluruh sisa pembayaran sebagai beban.
- Jika pembayaran dihapus atau status pembayaran diubah, pengeluaran otomatis terkait ikut dihapus/diperbarui melalui relasi database.
- Kategori beban dipetakan otomatis dari uraian utang, misalnya pakan menjadi kategori Pakan.
- Pembayaran piutang tidak dibuat menjadi beban.

Penting: jangan mencatat pembelian kredit yang sama secara manual sebagai Pengeluaran Operasional sebelum dibayar, karena akan menyebabkan beban ganda.

## Deploy

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
python manage.py check
python manage.py migrate finance
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Migration yang diterapkan:

`finance.0015_operationalexpense_trade_payment_cash_basis`
