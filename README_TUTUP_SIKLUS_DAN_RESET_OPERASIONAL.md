# Perbaikan Tutup Siklus dan Siklus Baru

## Fitur baru
Pada menu **Siklus Budidaya** tersedia tombol **Tutup & Siklus Baru** untuk pemilik/owner.

Saat tombol dijalankan, aplikasi akan:

1. Mengubah siklus lama menjadi **Selesai** dan menguncinya sebagai arsip.
2. Membuat snapshot KPI akhir siklus lama.
3. Membuat siklus berikutnya dengan status **Persiapan**.
4. Memilih siklus baru secara otomatis pada session pengguna.
5. Menyalin target DOC, size, biomassa, SR, FCR, ADG, estimasi harga, dan target biaya.
6. Memulai seluruh nilai realisasi operasional siklus baru dari nol tanpa menghapus riwayat lama.

## Nilai yang dimulai dari nol pada siklus baru
- Sampling, ABW, size, ADG, SR, FCR, dan biomassa.
- Parameter harian, cek anco, data pakan, dan siphon/mortalitas.
- Panen parsial dan panen total.
- Estimasi sisa udang berbasis FR dan Index.
- Omzet, penjualan, dan pengeluaran yang terikat pada siklus.
- Grafik dan ringkasan dashboard produksi siklus.

## Data yang tetap dipertahankan
- Master kolam, pelanggan, supplier, pengguna, pakan, obat, dan aset.
- Seluruh histori transaksi siklus lama.
- Snapshot dan laporan akhir siklus lama.
- Saldo keuangan lintas periode yang memang tidak bersifat operasional per siklus.

Data tidak dihapus. Pemisahan dilakukan menggunakan ForeignKey `cycle` dan filter siklus terpilih.

## Deployment
Tidak ada perubahan model dan tidak memerlukan migration.

Setelah upload ke VPS:

```bash
source env/bin/activate
python manage.py check
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```
