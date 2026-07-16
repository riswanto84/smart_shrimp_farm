"""Layanan cuaca aktual untuk lokasi tambak.

Sumber utama: Open-Meteo Forecast API.

Prinsip implementasi:
- data yang ditampilkan berasal dari API cuaca, bukan angka dummy;
- request dibuat sesederhana mungkin agar stabil pada VPS;
- retry otomatis untuk 429/5xx dan fallback IPv4;
- hasil sukses disimpan pada cache Django dan cache berkas bersama;
- kegagalan API tidak pernah mengganti data terakhir yang valid dengan nilai kosong;
- cache berkas dapat dipakai lintas worker Gunicorn dan setelah service restart.

Data ini adalah cuaca udara pada koordinat tambak, bukan suhu air kolam.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from requests.adapters import HTTPAdapter
from urllib3.util import connection as urllib3_connection
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

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
    """Ubah derajat arah angin menjadi label Indonesia yang mudah dibaca."""
    value = _safe_number(degrees, -1)
    if value < 0:
        return "—"

    directions = [
        ("↑", "Utara"),
        ("↗", "Timur Laut"),
        ("→", "Timur"),
        ("↘", "Tenggara"),
        ("↓", "Selatan"),
        ("↙", "Barat Daya"),
        ("←", "Barat"),
        ("↖", "Barat Laut"),
    ]
    arrow, label = directions[int((value + 22.5) // 45) % 8]
    return f"{arrow} {label}"


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
    elif 0 < temperature <= 24:
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


def _parse_api_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    except (TypeError, ValueError):
        return None


def _parse_payload(payload: dict[str, Any]) -> dict[str, Any]:
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}

    if current.get("temperature_2m") is None:
        raise ValueError("Respons API tidak memiliki current.temperature_2m")

    code = int(current.get("weather_code") or 0)
    condition, icon = WEATHER_CODES.get(code, ("Kondisi tidak diketahui", "fa-cloud"))

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
        # Open-Meteo sekarang dapat mengembalikan probabilitas hujan di blok current.
        "rain_chance": current.get("precipitation_probability"),
        "cloud_cover": current.get("cloud_cover"),
        # Gunakan surface_pressure sesuai endpoint yang terbukti berhasil pada VPS.
        "pressure": current.get("surface_pressure", current.get("pressure_msl")),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_direction": _wind_direction(current.get("wind_direction_10m")),
        "wind_direction_degrees": current.get("wind_direction_10m"),
        "condition": condition,
        "weather_code": code,
        "icon": icon,
        "is_day": bool(current.get("is_day", 1)),
        "updated_at": _parse_api_datetime(current.get("time")) or timezone.localtime(),
        "today_max": (daily.get("temperature_2m_max") or [None])[0],
        "today_min": (daily.get("temperature_2m_min") or [None])[0],
        "status": "live",
        "message": "Data cuaca API terbaru pada koordinat tambak",
    }
    data["farm_advice"] = _build_farm_advice(data)
    return data


def _build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.trust_env = bool(getattr(settings, "WEATHER_TRUST_ENV", False))
    session.headers.update({
        "User-Agent": "SmartShrimpFarm/1.2 (+https://smart.udangemasnusantara.co.id)",
        "Accept": "application/json",
        "Connection": "close",
    })
    return session


def _request_weather(url: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
    with _build_session() as session:
        response = session.get(url, params=params, timeout=(timeout, timeout + 8))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Respons API bukan objek JSON")
        return payload


def _request_weather_ipv4(url: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
    """Ulangi request memakai IPv4 jika VPS memiliki rute IPv6 yang bermasalah."""
    original = urllib3_connection.allowed_gai_family
    try:
        urllib3_connection.allowed_gai_family = lambda: socket.AF_INET
        return _request_weather(url, params, timeout)
    finally:
        urllib3_connection.allowed_gai_family = original


def _cache_file(latitude: float, longitude: float) -> Path:
    # /tmp dipilih sebagai default agar dapat ditulis baik oleh command root maupun
    # worker Gunicorn. Lokasi dapat diganti melalui WEATHER_FILE_CACHE_DIR.
    default_dir = Path(tempfile.gettempdir()) / "smart_shrimp_farm_weather"
    cache_dir = Path(getattr(settings, "WEATHER_FILE_CACHE_DIR", default_dir))
    digest = hashlib.sha1(f"{latitude:.5f}:{longitude:.5f}".encode()).hexdigest()[:12]
    return cache_dir / f"last_good_{digest}.json"


def _serialize_for_disk(data: dict[str, Any]) -> dict[str, Any]:
    serializable = dict(data)
    updated_at = serializable.get("updated_at")
    if isinstance(updated_at, datetime):
        serializable["updated_at"] = updated_at.isoformat()
    serializable["saved_at"] = timezone.now().isoformat()
    return serializable


def _write_disk_cache(path: Path, data: dict[str, Any]) -> None:
    """Simpan data valid secara atomik agar dapat dipakai semua worker Gunicorn."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Cache berisi data publik. Mode longgar menghindari konflik ownership
        # antara command yang dijalankan root dan worker Gunicorn (www-data).
        try:
            path.parent.chmod(0o777)
        except OSError:
            pass
        temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(_serialize_for_disk(data), ensure_ascii=False),
            encoding="utf-8",
        )
        try:
            temporary.chmod(0o666)
        except OSError:
            pass
        os.replace(temporary, path)
        try:
            path.chmod(0o666)
        except OSError:
            pass
    except OSError as exc:
        logger.warning("Gagal menyimpan cache cuaca berkas %s: %s", path, exc)


def _read_disk_cache(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("temperature") is None:
            return None

        saved_at = _parse_api_datetime(payload.pop("saved_at", None))
        max_age = int(getattr(settings, "WEATHER_STALE_SECONDS", 172800))
        if saved_at and timezone.now() - saved_at > timedelta(seconds=max_age):
            return None

        payload["updated_at"] = _parse_api_datetime(payload.get("updated_at"))

        # Normalisasi cache lama yang pernah menyimpan singkatan satu huruf
        # seperti "T". Jika derajat arah tersedia, selalu hitung ulang label
        # lengkap agar tampilan menjadi "→ Timur", "↗ Timur Laut", dst.
        degrees = payload.get("wind_direction_degrees")
        direction = str(payload.get("wind_direction") or "").strip()
        legacy_labels = {"U", "TL", "T", "TG", "S", "BD", "B", "BL"}
        if degrees is not None:
            payload["wind_direction"] = _wind_direction(degrees)
        elif direction in legacy_labels or len(direction) <= 2:
            payload["wind_direction"] = "—"

        payload["ok"] = True
        payload["status"] = "cache"
        payload["message"] = "API sementara tidak tersedia; menampilkan data cuaca terakhir yang valid"
        payload["farm_advice"] = _build_farm_advice(payload)
        return payload
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _offline_payload(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "offline",
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "location": getattr(settings, "WEATHER_LOCATION_NAME", "Muara Gembong"),
        "condition": "Data cuaca tidak tersedia",
        "icon": "fa-cloud-circle-exclamation",
        "temperature": None,
        "apparent_temperature": None,
        "humidity": None,
        "rain_chance": None,
        "wind_speed": None,
        "wind_direction": "—",
        "pressure": None,
        "today_min": None,
        "today_max": None,
        "updated_at": None,
        "message": "Gagal mengambil data cuaca dari API dan belum ada cache valid",
        "error": f"{type(exc).__name__}: {exc}",
        "farm_advice": [{
            "level": "warning",
            "icon": "fa-triangle-exclamation",
            "text": "Gunakan pengamatan lapangan dan alat ukur tambak sampai API kembali tersedia.",
        }],
    }


def get_farm_weather(force_refresh: bool = False) -> dict[str, Any]:
    """Ambil data cuaca aktual dengan cache lintas-worker dan fallback aman."""
    latitude = float(
        getattr(settings, "WEATHER_LATITUDE", getattr(settings, "FARM_LAT", -5.98))
    )
    longitude = float(
        getattr(settings, "WEATHER_LONGITUDE", getattr(settings, "FARM_LON", 107.02))
    )
    cache_key = f"ssf_weather_current_v5:{latitude:.5f}:{longitude:.5f}"
    ttl = max(60, int(getattr(settings, "WEATHER_CACHE_SECONDS", 600)))
    disk_path = _cache_file(latitude, longitude)

    if not force_refresh:
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and cached.get("temperature") is not None:
            degrees = cached.get("wind_direction_degrees")
            direction = str(cached.get("wind_direction") or "").strip()
            if degrees is not None:
                cached["wind_direction"] = _wind_direction(degrees)
            elif direction in {"U", "TL", "T", "TG", "S", "BD", "B", "BL"} or len(direction) <= 2:
                cached["wind_direction"] = "—"
            return cached

        # Cache berkas dibaca SEBELUM request API. Ini penting pada VPS karena
        # management command dan worker Gunicorn dapat memakai user/proses berbeda.
        # Data yang baru berhasil diambil oleh check_weather_api langsung dapat
        # ditampilkan oleh dashboard meskipun worker sedang mengalami kendala jaringan.
        disk_cached = _read_disk_cache(disk_path)
        if disk_cached:
            cache.set(cache_key, disk_cached, min(ttl, 300))
            return disk_cached

    timeout = float(getattr(settings, "WEATHER_API_TIMEOUT", 12))
    api_url = str(
        getattr(settings, "WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast")
    ).strip()

    # Query minimal ini disamakan dengan request yang terbukti memberi HTTP 200
    # pada VPS. Hindari hourly dan parameter tambahan yang sempat memicu HTTP 503.
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation_probability",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "surface_pressure",
            "is_day",
        ]),
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": getattr(settings, "WEATHER_TIMEZONE", "Asia/Jakarta"),
        "forecast_days": 1,
    }

    try:
        payload = _request_weather(api_url, params, timeout)
    except (requests.RequestException, ValueError, KeyError, OSError) as first_exc:
        logger.warning("Weather API request gagal; mencoba IPv4: %s", first_exc)
        try:
            payload = _request_weather_ipv4(api_url, params, timeout)
        except (requests.RequestException, ValueError, KeyError, OSError) as final_exc:
            logger.exception("Weather API gagal pada VPS: %s", final_exc)
            stale = _read_disk_cache(disk_path)
            if stale:
                cache.set(cache_key, stale, min(ttl, 300))
                return stale
            # Jangan cache payload kosong/offline. Request berikutnya boleh mencoba lagi.
            return _offline_payload(final_exc)

    try:
        weather = _parse_payload(payload)
    except (ValueError, KeyError, TypeError) as exc:
        logger.exception("Respons Weather API tidak dapat diproses: %s", exc)
        stale = _read_disk_cache(disk_path)
        if stale:
            cache.set(cache_key, stale, min(ttl, 300))
            return stale
        return _offline_payload(exc)

    cache.set(cache_key, weather, ttl)
    _write_disk_cache(disk_path, weather)
    return weather
