import os

from django.core.asgi import get_asgi_application

# This has to be here, otherwise "django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet." is raised
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fdm.settings.base")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

import fdm.websockets.urls  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(URLRouter(fdm.websockets.urls.websocket_urlpatterns)),
    },
)
