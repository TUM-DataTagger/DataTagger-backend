from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from fdm.cms.models.models import Content


@receiver(pre_delete, sender=Content)
def pre_delete(sender, instance, **kwargs):
    raise PermissionDenied
