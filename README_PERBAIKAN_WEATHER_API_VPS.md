# Perbaikan Weather API pada VPS

Perbaikan ini menambahkan:

- retry otomatis untuk kegagalan koneksi sementara dan HTTP 429/5xx;
- bypass proxy environment yang sering menyebabkan request VPS gagal;
- fallback IPv4 jika VPS memiliki rute IPv6 yang bermasalah;
- timeout lebih aman;
- cache hanya untuk data berhasil dan fallback data terakhir;
- log error lengkap di Gunicorn;
- management command diagnostik.

## Konfigurasi `.env`

```env
WEATHER_API_URL=https://api.open-meteo.com/v1/forecast
WEATHER_LOCATION_NAME=Muara Gembong
WEATHER_LATITUDE=-5.98
WEATHER_LONGITUDE=107.02
WEATHER_TIMEZONE=Asia/Jakarta
WEATHER_CACHE_SECONDS=600
WEATHER_API_TIMEOUT=10
WEATHER_TRUST_ENV=False
```

`WEATHER_TRUST_ENV=False` membuat library Requests mengabaikan HTTP_PROXY atau
HTTPS_PROXY lama yang mungkin tersimpan pada service Gunicorn.

## Instalasi dan pengujian

```bash
cd /var/www/uen/smart_shrimp_farm
source env/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py check_weather_api --refresh
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

Jika masih gagal, lihat error sebenarnya:

```bash
sudo journalctl -u gunicorn -n 100 --no-pager
python manage.py check_weather_api --refresh
```
