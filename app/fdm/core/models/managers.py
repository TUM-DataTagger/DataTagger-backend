from django.db import models

__all__ = [
    "BaseManager",
]


class BaseManager(models.Manager):
    """Manager BaseManager

    This is the manager class all other managers should inherit from.
    """

    use_for_related_fields = True
