# Penambahan Field Keterangan Penggajian

Perubahan:
- Label field `notes` pada transaksi penggajian menjadi **Keterangan**.
- Keterangan tampil pada form gaji, detail periode, laporan penggajian, slip gaji, dan ekspor Excel.
- Keterangan ikut diteruskan ke Pengeluaran Operasional saat gaji lunas disinkronkan.
- Migration baru: `payroll/migrations/0002_alter_payrollrecord_notes.py`.

Setelah deployment:

```bash
python manage.py migrate payroll
python manage.py check
```
