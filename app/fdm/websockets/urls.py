from django.urls import path

from fdm.websockets.consumers import WebsocketConsumer

websocket_urlpatterns = [
    path(r"ws/", WebsocketConsumer.as_asgi()),
]
