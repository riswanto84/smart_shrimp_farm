# Target Produksi per Siklus

Pembaruan ini memindahkan target Dashboard Produksi dari angka hardcode ke Master Siklus Budidaya.

## Field target baru
- Target DOC
- Target size (ekor/kg)
- Target biomassa/produksi (ton)
- Target SR (%)
- Target FCR
- Target ADG (g/hari)
- Target populasi hidup
- Harga jual estimasi per kg
- Target biaya produksi

Target diisi atau diperbarui melalui menu Siklus Budidaya. Dashboard Produksi otomatis memakai target dari siklus yang dipilih untuk garis target, progress biomassa, proyeksi target DOC, estimasi tanggal target size, target omzet, dan target laba.

## Instalasi
```bash
source env/bin/activate
python manage.py migrate cultivation
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

Migration `cultivation.0003_cycle_production_targets` wajib diterapkan.
