from django.urls import include, path

from ..uploads.rest.views import TusUploadViewSet
from .routers import TusAPIRouter

app_name = "rest_framework_tus"

router = TusAPIRouter()
router.register(r"tus", TusUploadViewSet, basename="upload")

urlpatterns = [
    path(r"", include((router.urls, "fdm.rest_framework_tus"), namespace="api")),
]
