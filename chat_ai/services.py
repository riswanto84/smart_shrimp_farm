import time
import requests
from django.conf import settings


def ollama_health(timeout=3):
    """Cek status Ollama aktual melalui API /api/tags.

    Parameter timeout dibuat opsional agar pemanggilan dari dashboard/API dapat
    menentukan batas waktu tanpa menyebabkan TypeError.
    """
    base_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL", "gemma2:2b")
    started = time.perf_counter()

    try:
        response = requests.get(f"{base_url}/api/tags", timeout=timeout)
        latency_ms = round((time.perf_counter() - started) * 1000)
        response.raise_for_status()

        payload = response.json()
        models = [
            item.get("name")
            for item in payload.get("models", [])
            if item.get("name")
        ]
        model_available = model in models

        return {
            "ok": True,
            "status": "online" if model_available else "model_missing",
            "url": base_url,
            "model": model,
            "model_available": model_available,
            "models": models,
            "model_count": len(models),
            "latency_ms": latency_ms,
            "message": (
                "Ollama online"
                if model_available
                else f"Ollama online, tetapi model {model} belum tersedia"
            ),
        }

    except requests.Timeout:
        return {
            "ok": False,
            "status": "timeout",
            "url": base_url,
            "model": model,
            "model_available": False,
            "models": [],
            "model_count": 0,
            "latency_ms": None,
            "message": "Koneksi ke Ollama timeout",
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status": "offline",
            "url": base_url,
            "model": model,
            "model_available": False,
            "models": [],
            "model_count": 0,
            "latency_ms": None,
            "message": f"Ollama tidak dapat dihubungi: {exc}",
        }

    except (ValueError, TypeError) as exc:
        return {
            "ok": False,
            "status": "error",
            "url": base_url,
            "model": model,
            "model_available": False,
            "models": [],
            "model_count": 0,
            "latency_ms": None,
            "message": f"Respons Ollama tidak valid: {exc}",
        }


def ask_ollama(prompt, timeout=120):
    base_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL", "gemma2:2b")
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as exc:
        return f"Ollama belum tersedia atau gagal dihubungi: {exc}"
