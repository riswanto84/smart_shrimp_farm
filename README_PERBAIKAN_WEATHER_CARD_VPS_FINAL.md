# Perbaikan Weather Card VPS Final

Perbaikan ini membuat Dashboard dan perintah `check_weather_api` memakai satu layanan yang sama.

## Perubahan utama

- Query Open-Meteo disederhanakan dan disamakan dengan query yang berhasil HTTP 200 di VPS.
- Probabilitas hujan dibaca langsung dari blok `current`.
- Tekanan udara memakai `surface_pressure`.
- Retry otomatis dan fallback IPv4.
- Hasil sukses disimpan ke cache Django dan cache berkas bersama di `/tmp/smart_shrimp_farm_weather/` agar dapat dipakai lintas worker Gunicorn.
- Hasil gagal tidak pernah disimpan sebagai cache utama.
- Jika API sementara 503, dashboard memakai data valid terakhir hingga 48 jam.

## Konfigurasi `.env`

```env
WEATHER_API_URL=https://api.open-meteo.com/v1/forecast
WEATHER_LOCATION_NAME=Muara Gembong
WEATHER_LATITUDE=-5.98
WEATHER_LONGITUDE=107.02
WEATHER_TIMEZONE=Asia/Jakarta
WEATHER_CACHE_SECONDS=600
WEATHER_API_TIMEOUT=12
WEATHER_STALE_SECONDS=172800
WEATHER_TRUST_ENV=False
```

## Instalasi VPS

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py check_weather_api --refresh
sudo systemctl restart smartshrimp
sudo systemctl restart nginx
```

Cache berkas default dibuat otomatis di `/tmp/smart_shrimp_farm_weather/`, sehingga tidak memerlukan pengaturan izin folder project. Lokasi ini dapat diganti lewat `WEATHER_FILE_CACHE_DIR` bila diperlukan.
