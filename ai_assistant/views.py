import json

from django.contrib.auth.decorators import login_required
from django.http import (
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .services.ollama_service import (
    OllamaServiceError,
    stream_chat,
)


@login_required
def chat_page(request):
    return render(
        request,
        "ai_assistant/chat.html",
    )


def encode_sse(
    event: str,
    data: dict,
) -> str:
    payload = json.dumps(
        data,
        ensure_ascii=False,
    )

    return (
        f"event: {event}\n"
        f"data: {payload}\n\n"
    )


@login_required
@require_POST
def chat_stream(request):
    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "error": "Format permintaan tidak valid.",
            },
            status=400,
        )

    question = str(
        payload.get("message", "")
    ).strip()

    if not question:
        return JsonResponse(
            {
                "error": "Pertanyaan tidak boleh kosong.",
            },
            status=400,
        )

    if len(question) > 5000:
        return JsonResponse(
            {
                "error": "Pertanyaan terlalu panjang.",
            },
            status=400,
        )

    messages = [
        {
            "role": "system",
            "content": (
                "Anda adalah Smart Shrimp AI, asisten budidaya "
                "udang vaname. Jawab dalam bahasa Indonesia. "
                "Jangan mengarang data tambak. Apabila data "
                "tidak tersedia, nyatakan secara jelas."
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    def event_generator():
        try:
            yield encode_sse(
                "status",
                {
                    "message": (
                        "AI sedang menganalisis..."
                    ),
                },
            )

            for chunk in stream_chat(messages):
                yield encode_sse(
                    "token",
                    {
                        "content": chunk,
                    },
                )

            yield encode_sse(
                "done",
                {
                    "success": True,
                },
            )

        except OllamaServiceError as exc:
            yield encode_sse(
                "error",
                {
                    "message": str(exc),
                },
            )

        except GeneratorExit:
            # Browser menekan Stop atau menutup koneksi.
            return

        except Exception:
            yield encode_sse(
                "error",
                {
                    "message": (
                        "Terjadi kesalahan pada layanan AI."
                    ),
                },
            )

    response = StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream",
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"

    return response