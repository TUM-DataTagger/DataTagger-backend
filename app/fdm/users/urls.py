from fdm.core.utils.routers import get_api_router
from fdm.users.rest.views import *

__all__ = [
    "router",
    "urlpatterns",
]

router = get_api_router()

router.register(r"user", UserViewSet)

urlpatterns = []
