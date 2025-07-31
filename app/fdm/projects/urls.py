from fdm.core.utils.routers import get_api_router

from .rest.views import *

__all__ = [
    "router",
    "urlpatterns",
]

router = get_api_router()

router.register(r"project", ProjectViewSet, basename="project")
router.register(r"project-membership", ProjectMembershipViewSet, basename="project-membership")

urlpatterns = []
