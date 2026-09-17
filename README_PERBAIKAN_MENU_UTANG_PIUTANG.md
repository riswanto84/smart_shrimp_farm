# Perbaikan Menu Utang dan Piutang Usaha

Versi ini memastikan dua menu berikut tampil pada bagian **KEUANGAN & PAJAK**:

- Piutang Usaha — `/finance/tax/receivables/`
- Utang Usaha — `/finance/tax/payables/`

Fitur sudah mencakup pencatatan transaksi, jatuh tempo, pembayaran bertahap, saldo, status lunas/sebagian, aging, PDF, serta integrasi saldo ke Neraca.

## Instalasi

```bash
python manage.py migrate
python manage.py check
python manage.py check_trade_accounts
python manage.py collectstatic --noinput
```

Restart Gunicorn dan Nginx, kemudian lakukan hard refresh browser.

```bash
sudo systemctl restart smartshrimp
sudo systemctl restart nginx
```

Apabila menu belum terlihat, pastikan folder `accounts`, `finance`, dan `templates` dari ZIP ini benar-benar menimpa versi lama. Menu didefinisikan di `accounts/rbac.py`.
