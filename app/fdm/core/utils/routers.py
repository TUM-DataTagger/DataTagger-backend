from rest_framework import routers

__all__ = [
    "get_api_router",
]

__router = None


def get_api_router():
    """
    Singleton pattern for getting a DRF router
    :return:
    """
    global __router

    if not __router:
        __router = routers.DefaultRouter()
    return __router
