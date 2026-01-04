"""WebSocket URL 라우팅 설정."""

from django.urls import path

from apps.chat.consumers import ChatConsumer

websocket_urlpatterns = [
    path("ws/chat/<int:room_id>/", ChatConsumer.as_asgi()),
]
