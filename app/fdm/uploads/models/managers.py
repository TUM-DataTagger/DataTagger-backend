from fdm.core.models.managers import BaseManager

from .querysets import *

__all__ = [
    "UploadsVersionManager",
    "UploadsDatasetManager",
]


class UploadsVersionManager(BaseManager.from_queryset(UploadsVersionQuerySet)):
    pass


class UploadsDatasetManager(BaseManager.from_queryset(UploadsDatasetQuerySet)):
    pass
