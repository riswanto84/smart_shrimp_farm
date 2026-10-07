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


def _tool_message(response):
    return response.get('message') or {}


def _tool_calls(message):
    calls = message.get('tool_calls') or []
    normalized = []
    for call in calls:
        fn = call.get('function') if isinstance(call, dict) else getattr(call, 'function', None)
        if not fn:
            continue
        if isinstance(fn, dict):
            name = fn.get('name')
            args = fn.get('arguments') or {}
        else:
            name = getattr(fn, 'name', None)
            args = getattr(fn, 'arguments', {}) or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        normalized.append({'name': name, 'arguments': args})
    return normalized


def stream_ollama_agent(messages, model=None, images=None, timeout=None, tools=None,
                        execute_tool=None, current_cycle_id=None, current_pond_id=None,
                        max_tool_rounds=6):
    """Run a read-only Ollama tool-calling loop, then stream the final answer.

    Tool execution happens inside Django, so the model never gets DB credentials
    and never executes SQL. If the model does not request a tool, this falls back
    to the normal streaming endpoint.
    """
    model = model or active_model()
    base_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    timeout = timeout or getattr(settings, 'AI_GATEWAY_TIMEOUT', 300)
    if not tools or not execute_tool:
        yield from stream_ollama(messages, model=model, images=images, timeout=timeout)
        return

    working = [dict(m) for m in messages]
    if images and working:
        working[-1] = dict(working[-1])
        working[-1]['images'] = images

    for _ in range(max_tool_rounds):
        response = requests.post(
            f'{base_url}/api/chat',
            json={'model': model, 'messages': working, 'tools': tools, 'stream': False, 'think': False},
            timeout=(10, timeout),
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('error'):
            raise RuntimeError(payload['error'])
        message = _tool_message(payload)
        calls = _tool_calls(message)
        if not calls:
            # Stream a clean final answer using the accumulated conversation.
            yield from stream_ollama(working, model=model, timeout=timeout)
            return

        working.append(message)
        for call in calls:
            result = execute_tool(
                call['name'], call['arguments'],
                current_cycle_id=current_cycle_id,
                current_pond_id=current_pond_id,
            )
            working.append({
                'role': 'tool',
                'content': json.dumps(result, ensure_ascii=False, default=str),
            })

    raise RuntimeError('AI mencapai batas putaran tool calling tanpa menghasilkan jawaban final.')
