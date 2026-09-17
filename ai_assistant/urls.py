from django.urls import path, include

from . import views

app_name = "ai_assistant"

urlpatterns = [
    path(
        "",
        views.chat_page,
        name="chat",
    ),
    path(
        "stream/",
        views.chat_stream,
        name="chat_stream",
    ),
    path(
        "ai-assistant/",
        include("ai_assistant.urls"),
    ),
]