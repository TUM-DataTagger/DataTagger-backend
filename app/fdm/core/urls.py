from django.conf import settings

from fdm.core.rest.views import *
from fdm.core.utils.routers import get_api_router

__all__ = [
    "router",
    "urlpatterns",
]

router = get_api_router()

router.register(r"auth", ObtainJSONWebTokenViewSet, basename="auth")
router.register(r"authrefresh", RefreshJSONWebTokenViewSet, basename="authrefresh")
router.register(r"authverify", VerifyJSONWebTokenViewSet, basename="authverify")
router.register(r"authjwtcookie", JWTCookieViewSet, basename="authjwtcookie")
if settings.DEBUG:
    router.register(r"reset-backend", ResetBackendView, basename="reset-backend")

urlpatterns = []
