import time
import requests
from django.conf import settings


def _gateway_enabled():
    return bool(getattr(settings, "AI_GATEWAY_URL", "").strip())


def _gateway_headers():
    key = getattr(settings, "AI_GATEWAY_API_KEY", "")
    return {"X-AI-Gateway-Key": key} if key else {}


def ollama_health(timeout=3):
    """Cek kesehatan AI Gateway Node.js, dengan fallback langsung ke Ollama."""
    model = getattr(settings, "AI_GATEWAY_MODEL", None) or getattr(settings, "OLLAMA_MODEL", "gemma2:2b")
    started = time.perf_counter()

    if _gateway_enabled():
        base_url = settings.AI_GATEWAY_URL.rstrip("/")
        try:
            response = requests.get(
                f"{base_url}/health",
                headers=_gateway_headers(),
                timeout=timeout,
            )
            latency_ms = round((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            payload = response.json()
            models = payload.get("available_models", [])
            return {
                "ok": payload.get("status") == "online",
                "status": payload.get("status", "online"),
                "url": base_url,
                "model": payload.get("model", model),
                "model_available": model in models if models else True,
                "models": models,
                "model_count": len(models),
                "latency_ms": latency_ms,
                "message": "AI Gateway Node.js online",
                "gateway": True,
            }
        except requests.Timeout:
            return {
                "ok": False, "status": "timeout", "url": base_url,
                "model": model, "model_available": False, "models": [],
                "model_count": 0, "latency_ms": None,
                "message": "AI Gateway Node.js timeout", "gateway": True,
            }
        except (requests.RequestException, ValueError, TypeError) as exc:
            # Fallback langsung ke Ollama bila gateway sedang mati.
            gateway_error = str(exc)
        else:
            gateway_error = ""
    else:
        gateway_error = "AI_GATEWAY_URL belum diatur"

    base_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434").rstrip("/")
    started = time.perf_counter()
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=timeout)
        latency_ms = round((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        payload = response.json()
        models = [item.get("name") for item in payload.get("models", []) if item.get("name")]
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
            "message": "Ollama online (fallback langsung)" if gateway_error else "Ollama online",
            "gateway": False,
            "gateway_error": gateway_error,
        }
    except requests.Timeout:
        status, message = "timeout", "Koneksi AI timeout"
    except requests.RequestException as exc:
        status, message = "offline", f"AI tidak dapat dihubungi: {exc}"
    except (ValueError, TypeError) as exc:
        status, message = "error", f"Respons AI tidak valid: {exc}"

    return {
        "ok": False, "status": status, "url": base_url, "model": model,
        "model_available": False, "models": [], "model_count": 0,
        "latency_ms": None, "message": message, "gateway": False,
        "gateway_error": gateway_error,
    }


def ask_ollama(prompt, timeout=120):
    """Kirim prompt melalui Node.js AI Gateway; fallback langsung ke Ollama."""
    model = getattr(settings, "AI_GATEWAY_MODEL", None) or getattr(settings, "OLLAMA_MODEL", "gemma2:2b")

    if _gateway_enabled():
        base_url = settings.AI_GATEWAY_URL.rstrip("/")
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                headers={**_gateway_headers(), "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            answer = payload.get("message") or payload.get("response") or ""
            if answer:
                return answer
        except requests.RequestException:
            # Gateway opsional; sistem tetap berjalan lewat Ollama langsung.
            pass

    base_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434").rstrip("/")
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as exc:
        return f"Ollama/AI Gateway belum tersedia atau gagal dihubungi: {exc}"


class OllamaStreamError(Exception):
    """Kesalahan komunikasi saat melakukan streaming dari Ollama."""


def stream_ollama_chat(messages, options=None):
    """Yield potongan teks dari endpoint /api/chat Ollama secara real-time."""
    import json

    model = getattr(settings, "AI_GATEWAY_MODEL", None) or getattr(settings, "OLLAMA_MODEL", "gemma2:2b")
    connect_timeout = getattr(settings, "OLLAMA_CONNECT_TIMEOUT", 10)
    read_timeout = getattr(settings, "OLLAMA_READ_TIMEOUT", 300)
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": options or {"temperature": 0.2},
    }

    # Gateway dipakai bila mendukung streaming NDJSON. Bila gagal sebelum token
    # pertama, otomatis fallback langsung ke Ollama.
    endpoints = []
    if _gateway_enabled():
        endpoints.append((
            f"{settings.AI_GATEWAY_URL.rstrip('/')}/api/chat",
            {**_gateway_headers(), "Content-Type": "application/json"},
        ))
    endpoints.append((
        f"{getattr(settings, 'OLLAMA_URL', 'http://localhost:11434').rstrip('/')}/api/chat",
        {"Content-Type": "application/json"},
    ))

    last_error = None
    for url, headers in endpoints:
        emitted = False
        try:
            with requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(connect_timeout, read_timeout),
            ) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    try:
                        data = json.loads(raw_line)
                    except (ValueError, TypeError):
                        continue
                    if data.get("error"):
                        raise OllamaStreamError(str(data["error"]))
                    content = (data.get("message") or {}).get("content", "")
                    if not content:
                        content = data.get("response", "")
                    if content:
                        emitted = True
                        yield content
                    if data.get("done"):
                        return
                if emitted:
                    return
        except requests.Timeout as exc:
            last_error = OllamaStreamError("Koneksi AI mengalami timeout.")
        except requests.ConnectionError as exc:
            last_error = OllamaStreamError("Server Ollama/AI Gateway tidak dapat dihubungi.")
        except requests.RequestException as exc:
            last_error = OllamaStreamError(f"Kesalahan komunikasi AI: {exc}")
        except OllamaStreamError as exc:
            last_error = exc
        if emitted:
            raise last_error

    raise last_error or OllamaStreamError("Layanan AI tidak menghasilkan respons.")
