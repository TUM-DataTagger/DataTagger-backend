from django.apps import AppConfig

__all__ = [
    "WebsocketsConfig",
]


class WebsocketsConfig(AppConfig):
    name = "fdm.websockets"

    def ready(self):
        # import handlers here so they are registered when the application starts
        import fdm.websockets.consumers.handlers
