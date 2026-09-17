import json
from collections.abc import Generator

import requests
from django.conf import settings


class OllamaServiceError(Exception):
    """Kesalahan komunikasi dengan layanan Ollama."""


def stream_chat(
    messages: list[dict[str, str]],
) -> Generator[str, None, None]:
    """
    Mengirim pesan ke Ollama dan menghasilkan potongan jawaban
    satu per satu.
    """

    url = f"{settings.OLLAMA_BASE_URL}/api/chat"

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.2,
        },
    }

    timeout = (
        settings.OLLAMA_CONNECT_TIMEOUT,
        settings.OLLAMA_READ_TIMEOUT,
    )

    try:
        with requests.post(
            url,
            json=payload,
            stream=True,
            timeout=timeout,
        ) as response:
            response.raise_for_status()

            for raw_line in response.iter_lines(
                decode_unicode=True
            ):
                if not raw_line:
                    continue

                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                if data.get("error"):
                    raise OllamaServiceError(data["error"])

                content = (
                    data.get("message", {}).get("content", "")
                )

                if content:
                    yield content

                if data.get("done"):
                    break

    except requests.ConnectTimeout as exc:
        raise OllamaServiceError(
            "Koneksi ke server Ollama mengalami timeout."
        ) from exc

    except requests.ConnectionError as exc:
        raise OllamaServiceError(
            "Server Ollama tidak dapat dihubungi."
        ) from exc

    except requests.RequestException as exc:
        raise OllamaServiceError(
            f"Kesalahan komunikasi dengan Ollama: {exc}"
        ) from exc