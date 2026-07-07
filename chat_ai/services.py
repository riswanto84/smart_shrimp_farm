import requests
from django.conf import settings


def ollama_health():
    """Cek koneksi Ollama lokal agar user tahu model sudah tersambung atau belum."""
    base_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    model = getattr(settings, 'OLLAMA_MODEL', 'gemma2:2b')
    try:
        response = requests.get(f'{base_url}/api/tags', timeout=5)
        response.raise_for_status()
        models = [m.get('name') for m in response.json().get('models', [])]
        return {
            'ok': True,
            'url': base_url,
            'model': model,
            'models': models,
            'message': 'Ollama tersambung',
        }
    except Exception as exc:
        return {
            'ok': False,
            'url': base_url,
            'model': model,
            'models': [],
            'message': f'Ollama belum tersambung: {exc}',
        }


def ask_ollama(prompt):
    base_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    model = getattr(settings, 'OLLAMA_MODEL', 'gemma2:2b')
    try:
        r = requests.post(
            f'{base_url}/api/generate',
            json={'model': model, 'prompt': prompt, 'stream': False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get('response', '')
    except Exception as e:
        return f'Ollama belum tersedia atau gagal dihubungi: {e}'
