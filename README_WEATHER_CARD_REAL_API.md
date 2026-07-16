# Weather Card Real API

Weather Card menggunakan Open-Meteo Forecast API pada koordinat tambak. Tidak ada angka suhu hardcode.

## Konfigurasi opsional `.env`

```env
WEATHER_LOCATION_NAME=Muara Gembong
WEATHER_LATITUDE=-5.98
WEATHER_LONGITUDE=107.02
WEATHER_TIMEZONE=Asia/Jakarta
WEATHER_CACHE_SECONDS=600
WEATHER_API_TIMEOUT=5
```

Open-Meteo tidak memerlukan API key pada paket publiknya. Data disimpan di cache 10 menit agar halaman tidak memanggil API berulang kali. Jika API sementara gagal, aplikasi menampilkan cache terakhir dengan label `cache`; jika belum ada cache, tampil status API tidak tersedia.

Catatan: cuaca ini adalah data model/API berdasarkan koordinat, bukan sensor suhu air kolam. Pengambilan keputusan budidaya tetap mengutamakan hasil pengukuran lapangan.
