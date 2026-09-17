# Perbaikan Rekonsiliasi Saldo Awal

## Perubahan

- Halaman **Saldo Awal** ditingkatkan menjadi wizard rekonsiliasi.
- Ditambahkan input Persediaan Awal, Uang Muka, Aset Lancar Lainnya, Utang Pajak, Utang Pemilik, Utang Lainnya, Tambahan Modal, dan Prive.
- Piutang Usaha, Utang Usaha, Aset Tetap, Akumulasi Penyusutan, serta Laba/Rugi Berjalan tetap ditarik otomatis dari modul masing-masing agar tidak tercatat ganda.
- Ditambahkan pratinjau langsung persamaan neraca.
- Ditambahkan tombol **Rekonsiliasi Otomatis** yang menghitung Modal Pemilik agar selisih neraca menjadi nol.
- Prive otomatis disimpan sebagai pengurang ekuitas.
- Tidak ada perubahan struktur database dan tidak memerlukan migration baru.

## Setelah unggah ke VPS

```bash
source env/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Buka menu **Keuangan & Pajak > Saldo Awal**, lengkapi akun berdasarkan bukti, lalu gunakan Rekonsiliasi Otomatis hanya setelah seluruh nilai aset dan kewajiban diverifikasi.
