from fdm.core.utils.routers import get_api_router

from .rest.views import *

__all__ = [
    "router",
    "urlpatterns",
]

router = get_api_router()

router.register(r"faq-category", FAQCategoryViewSet, basename="faq-category")

router.register(r"faq", FAQViewSet, basename="faq")

urlpatterns = []
