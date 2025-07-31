from fdm.core.utils.routers import get_api_router
from fdm.uploads.rest.views import *

__all__ = [
    "router",
    "urlpatterns",
]


router = get_api_router()

router.register(r"uploads-dataset", UploadsDatasetViewSet, basename="uploads-dataset")
router.register(r"uploads-version", UploadsVersionViewSet, basename="uploads-version")
router.register(r"uploads-version-file", UploadsVersionFileViewSet, basename="uploads-version-file")

urlpatterns = []
