# Perbaikan Weather Card pada proses web/Gunicorn

Perbaikan ini menyelesaikan kondisi ketika `check_weather_api` berhasil tetapi dashboard tetap kosong.

- Cache cuaca dipindahkan ke folder bersama `runtime_cache/weather`.
- Worker web membaca cache berkas sebelum memanggil API.
- Dashboard memanggil service cuaca secara eksplisit.
- Endpoint `/weather/status/` menguji cuaca dari proses web yang sama.
- Jika render awal kosong, browser melakukan satu kali pemulihan otomatis.

Tambahkan ke `.env` bila diperlukan:

```env
WEATHER_FILE_CACHE_DIR=/var/www/uen/smart_shrimp_farm/runtime_cache/weather
```

Siapkan izin:

```bash
sudo install -d -o www-data -g www-data -m 775 /var/www/uen/smart_shrimp_farm/runtime_cache/weather
```
