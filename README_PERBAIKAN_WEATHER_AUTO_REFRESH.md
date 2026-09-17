# Perbaikan Weather Card Auto Refresh

Perubahan:

- Cache berkas cuaca tidak lagi menghentikan request API selamanya.
- Cache berkas hanya dipakai langsung selama masih dalam `WEATHER_CACHE_SECONDS`.
- Setelah TTL berakhir, aplikasi mencoba mengambil data Open-Meteo terbaru.
- Cache lama tetap dipakai sebagai fallback saat API gagal.
- Endpoint `/weather/status/?refresh=1` mengembalikan `updated_at` dan `checked_at`.
- Dashboard memeriksa cuaca otomatis 3 detik setelah dibuka dan setiap 5 menit.
- Data Weather Card diperbarui langsung tanpa reload seluruh halaman.
- Saat tab browser dibuka kembali, data diperiksa ulang.
- Label menampilkan waktu data API dan waktu pemeriksaan terakhir agar jelas bila sumber belum mengeluarkan titik data baru.

## Instalasi VPS

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate

python manage.py check
python manage.py collectstatic --noinput
sudo systemctl restart smartshrimp
sudo systemctl restart nginx
```

Disarankan pada `.env`:

```env
WEATHER_CACHE_SECONDS=300
WEATHER_STALE_SECONDS=172800
WEATHER_API_TIMEOUT=12
```

Tidak ada perubahan model/database sehingga tidak diperlukan migrasi.
