from django.db import models

from fdm.core.models import BaseModel

__all__ = [
    "Setting",
]


class Setting(BaseModel):
    key = models.CharField(
        primary_key=True,
        unique=True,
        max_length=255,
    )

    value = models.TextField(
        blank=True,
        null=True,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    public = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return self.key
