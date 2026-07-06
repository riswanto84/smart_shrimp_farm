import requests
from django.conf import settings

def ask_ollama(prompt):
    try:
        r=requests.post(f'{settings.OLLAMA_URL}/api/generate', json={'model':settings.OLLAMA_MODEL,'prompt':prompt,'stream':False}, timeout=120)
        r.raise_for_status()
        return r.json().get('response','')
    except Exception as e:
        return f'Ollama belum tersedia atau gagal dihubungi: {e}'
