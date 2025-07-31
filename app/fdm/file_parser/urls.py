from fdm.core.utils.routers import get_api_router

from .rest.views import *

__all__ = [
    "router",
    "urlpatterns",
]

router = get_api_router()

# Register your routes here
# Example: router.register(r"users", UserViewSet)


urlpatterns = []
