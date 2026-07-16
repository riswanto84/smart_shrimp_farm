"""Layanan cuaca publik untuk lokasi tambak.

Sumber default: Open-Meteo Forecast API. Data adalah observasi/model cuaca pada
koordinat tambak, bukan pembacaan sensor fisik di lokasi kolam.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

WEATHER_CODES = {
    0: ("Cerah", "fa-sun"),
    1: ("Cerah berawan", "fa-cloud-sun"),
    2: ("Berawan sebagian", "fa-cloud-sun"),
    3: ("Berawan", "fa-cloud"),
    45: ("Berkabut", "fa-smog"),
    48: ("Kabut berembun", "fa-smog"),
    51: ("Gerimis ringan", "fa-cloud-rain"),
    53: ("Gerimis", "fa-cloud-rain"),
    55: ("Gerimis lebat", "fa-cloud-showers-heavy"),
    56: ("Gerimis beku ringan", "fa-cloud-rain"),
    57: ("Gerimis beku", "fa-cloud-rain"),
    61: ("Hujan ringan", "fa-cloud-rain"),
    63: ("Hujan sedang", "fa-cloud-showers-heavy"),
    65: ("Hujan lebat", "fa-cloud-showers-heavy"),
    66: ("Hujan beku ringan", "fa-cloud-rain"),
    67: ("Hujan beku", "fa-cloud-rain"),
    71: ("Salju ringan", "fa-snowflake"),
    73: ("Salju", "fa-snowflake"),
    75: ("Salju lebat", "fa-snowflake"),
    77: ("Butiran salju", "fa-snowflake"),
    80: ("Hujan lokal ringan", "fa-cloud-rain"),
    81: ("Hujan lokal", "fa-cloud-showers-heavy"),
    82: ("Hujan lokal lebat", "fa-cloud-showers-heavy"),
    85: ("Hujan salju ringan", "fa-snowflake"),
    86: ("Hujan salju lebat", "fa-snowflake"),
    95: ("Badai petir", "fa-cloud-bolt"),
    96: ("Badai petir dan hujan es", "fa-cloud-bolt"),
    99: ("Badai petir berat", "fa-cloud-bolt"),
}


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _wind_direction(degrees: Any) -> str:
    value = _safe_number(degrees, -1)
    if value < 0:
        return "—"
    names = ["U", "TL", "T", "TG", "S", "BD", "B", "BL"]
    return names[int((value + 22.5) // 45) % 8]


def _build_farm_advice(data: dict[str, Any]) -> list[dict[str, str]]:
    advice: list[dict[str, str]] = []
    rain_chance = _safe_number(data.get("rain_chance"))
    temperature = _safe_number(data.get("temperature"))
    wind_speed = _safe_number(data.get("wind_speed"))
    pressure = _safe_number(data.get("pressure"))

    if rain_chance >= 70:
        advice.append({
            "level": "warning",
            "icon": "fa-cloud-showers-heavy",
            "text": "Peluang hujan tinggi. Pantau pH, salinitas, dan DO setelah hujan.",
        })
    elif rain_chance >= 40:
        advice.append({
            "level": "info",
            "icon": "fa-umbrella",
            "text": "Ada potensi hujan. Siapkan pemeriksaan kualitas air setelah perubahan cuaca.",
        })

    if temperature >= 33:
        advice.append({
            "level": "warning",
            "icon": "fa-temperature-high",
            "text": "Suhu udara tinggi. Hindari pemberian pakan berlebih saat siang terpanas.",
        })
    elif temperature <= 24 and temperature > 0:
        advice.append({
            "level": "info",
            "icon": "fa-temperature-low",
            "text": "Suhu udara relatif rendah. Pantau respons makan dan DO pagi hari.",
        })

    if wind_speed >= 30:
        advice.append({
            "level": "warning",
            "icon": "fa-wind",
            "text": "Angin cukup kencang. Periksa keamanan kincir, kabel, dan perlengkapan kolam.",
        })

    if pressure and pressure < 1005:
        advice.append({
            "level": "info",
            "icon": "fa-gauge-high",
            "text": "Tekanan udara rendah. Tingkatkan kewaspadaan terhadap penurunan DO malam hari.",
        })

    if not advice:
        advice.append({
            "level": "success",
            "icon": "fa-circle-check",
            "text": "Tidak ada peringatan cuaca utama. Operasional tetap mengikuti pengukuran air kolam.",
        })
    return advice[:3]


def _parse_payload(payload: dict[str, Any]) -> dict[str, Any]:
    current = payload.get("current") or {}
    hourly = payload.get("hourly") or {}
    daily = payload.get("daily") or {}

    code = int(current.get("weather_code") or 0)
    condition, icon = WEATHER_CODES.get(code, ("Kondisi tidak diketahui", "fa-cloud"))

    current_time = current.get("time")
    update_time = None
    if current_time:
        try:
            update_time = datetime.fromisoformat(str(current_time))
            if timezone.is_naive(update_time):
                update_time = timezone.make_aware(update_time, timezone.get_current_timezone())
        except (TypeError, ValueError):
            update_time = None

    rain_chance = None
    hourly_times = hourly.get("time") or []
    hourly_rain = hourly.get("precipitation_probability") or []
    if current_time and current_time in hourly_times:
        idx = hourly_times.index(current_time)
        if idx < len(hourly_rain):
            rain_chance = hourly_rain[idx]
    if rain_chance is None:
        rain_chance = (daily.get("precipitation_probability_max") or [None])[0]

    data = {
        "ok": True,
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "location": getattr(settings, "WEATHER_LOCATION_NAME", "Muara Gembong"),
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "temperature": current.get("temperature_2m"),
        "apparent_temperature": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "rain_chance": rain_chance,
        "cloud_cover": current.get("cloud_cover"),
        "pressure": current.get("pressure_msl"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_direction": _wind_direction(current.get("wind_direction_10m")),
        "condition": condition,
        "weather_code": code,
        "icon": icon,
        "is_day": bool(current.get("is_day", 1)),
        "updated_at": update_time or timezone.localtime(),
        "today_max": (daily.get("temperature_2m_max") or [None])[0],
        "today_min": (daily.get("temperature_2m_min") or [None])[0],
        "sunrise": (daily.get("sunrise") or [None])[0],
        "sunset": (daily.get("sunset") or [None])[0],
        "status": "live",
        "message": "Data cuaca API pada koordinat tambak",
    }
    data["farm_advice"] = _build_farm_advice(data)
    return data


def get_farm_weather(force_refresh: bool = False) -> dict[str, Any]:
    """Ambil cuaca lokasi tambak dengan cache dan stale fallback.

    Cache aktif mengurangi panggilan API di setiap halaman. Bila API tidak dapat
    dijangkau, cache lama dipakai agar UI tetap informatif dan diberi label cache.
    """
    cache_key = "ssf_weather_current_v2"
    stale_key = "ssf_weather_stale_v2"
    ttl = int(getattr(settings, "WEATHER_CACHE_SECONDS", 600))

    if not force_refresh:
        cached = cache.get(cache_key)
        if cached:
            return cached

    latitude = getattr(settings, "WEATHER_LATITUDE", getattr(settings, "FARM_LAT", -5.98))
    longitude = getattr(settings, "WEATHER_LONGITUDE", getattr(settings, "FARM_LON", 107.02))
    timeout = float(getattr(settings, "WEATHER_API_TIMEOUT", 5))

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "is_day",
            "precipitation",
            "rain",
            "weather_code",
            "cloud_cover",
            "pressure_msl",
            "wind_speed_10m",
            "wind_direction_10m",
        ]),
        "hourly": "precipitation_probability",
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "sunrise",
            "sunset",
        ]),
        "timezone": getattr(settings, "WEATHER_TIMEZONE", "Asia/Jakarta"),
        "forecast_days": 2,
    }

    try:
        response = requests.get(
            getattr(settings, "WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast"),
            params=params,
            timeout=timeout,
            headers={"User-Agent": "SmartShrimpFarm/1.0 (+https://smart.udangemasnusantara.co.id)"},
        )
        response.raise_for_status()
        weather = _parse_payload(response.json())
        cache.set(cache_key, weather, ttl)
        cache.set(stale_key, weather, 86400)
        return weather
    except (requests.RequestException, ValueError, KeyError) as exc:
        stale = cache.get(stale_key)
        if stale:
            stale = dict(stale)
            stale["status"] = "cache"
            stale["message"] = "API tidak terjangkau; menampilkan data terakhir tersimpan"
            stale["error"] = str(exc)
            return stale
        return {
            "ok": False,
            "status": "offline",
            "source": "Open-Meteo",
            "source_url": "https://open-meteo.com/",
            "location": getattr(settings, "WEATHER_LOCATION_NAME", "Muara Gembong"),
            "condition": "Data cuaca tidak tersedia",
            "icon": "fa-cloud-circle-exclamation",
            "temperature": None,
            "updated_at": None,
            "message": "Gagal mengambil data cuaca dari API",
            "error": str(exc),
            "farm_advice": [{
                "level": "warning",
                "icon": "fa-triangle-exclamation",
                "text": "Gunakan pengamatan lapangan dan alat ukur tambak sampai API kembali tersedia.",
            }],
        }
