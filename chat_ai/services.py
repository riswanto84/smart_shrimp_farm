import json
import time
import requests
from django.conf import settings


def _gateway_enabled():
    return bool(getattr(settings, 'AI_GATEWAY_URL', '').strip())


def _gateway_headers():
    key = getattr(settings, 'AI_GATEWAY_API_KEY', '')
    return {'X-AI-Gateway-Key': key} if key else {}


def active_model():
    return getattr(settings, 'AI_GATEWAY_MODEL', None) or getattr(settings, 'OLLAMA_MODEL', 'gemma2:2b')


def ollama_health(timeout=3):
    model = active_model()
    base_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    started = time.perf_counter()
    try:
        response = requests.get(f'{base_url}/api/tags', timeout=timeout)
        latency_ms = round((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        payload = response.json()
        models = [item.get('name') for item in payload.get('models', []) if item.get('name')]
        return {'ok': True, 'status': 'online' if model in models else 'model_missing', 'url': base_url,
                'model': model, 'model_available': model in models, 'models': models,
                'model_count': len(models), 'latency_ms': latency_ms,
                'message': 'Ollama online', 'gateway': False}
    except requests.Timeout:
        status, message = 'timeout', 'Koneksi AI timeout'
    except requests.RequestException as exc:
        status, message = 'offline', f'AI tidak dapat dihubungi: {exc}'
    except (ValueError, TypeError) as exc:
        status, message = 'error', f'Respons AI tidak valid: {exc}'
    return {'ok': False, 'status': status, 'url': base_url, 'model': model,
            'model_available': False, 'models': [], 'model_count': 0,
            'latency_ms': None, 'message': message, 'gateway': False}


def stream_ollama(messages, model=None, images=None, timeout=None):
    """Yield potongan teks dari endpoint /api/chat Ollama dalam format NDJSON."""
    model = model or active_model()
    base_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    timeout = timeout or getattr(settings, 'AI_GATEWAY_TIMEOUT', 300)
    outgoing = [dict(item) for item in messages]
    if images and outgoing:
        outgoing[-1]['images'] = images
    with requests.post(
        f'{base_url}/api/chat',
        json={'model': model, 'messages': outgoing, 'stream': True, 'think': False},
        stream=True,
        timeout=(10, timeout),
    ) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            payload = json.loads(raw_line)
            if payload.get('error'):
                raise RuntimeError(payload['error'])
            chunk = (payload.get('message') or {}).get('content', '')
            if chunk:
                yield chunk
            if payload.get('done'):
                break


def ask_ollama(prompt, timeout=120):
    try:
        return ''.join(stream_ollama([{'role': 'user', 'content': prompt}], timeout=timeout))
    except Exception as exc:
        return f'Ollama belum tersedia atau gagal dihubungi: {exc}'
