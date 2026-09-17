# Perbaikan Menu Prediksi Pertumbuhan pada VPS

Menu **Prediksi Pertumbuhan** kini disisipkan langsung oleh template sidebar global `templates/base.html` tepat setelah **Dashboard Produksi**.

Perbaikan ini tidak lagi bergantung pada hasil penyaringan `APP_MENU`, sehingga menu tetap muncul konsisten pada VPS untuk pengguna yang dapat melihat Dashboard Produksi.

## Penerapan

```bash
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Tidak memerlukan migrasi maupun `collectstatic`.
