from fdm.cms.rest.viewsets import ContentViewSet
from fdm.core.utils.routers import get_api_router

router = get_api_router()

router.register(r"cms", ContentViewSet, basename="cms")

urlpatterns = []
