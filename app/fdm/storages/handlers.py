from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from fdm.folders.models import Folder
from fdm.storages.models import DynamicStorage, Storage


@receiver(pre_delete, sender=Storage)
@receiver(pre_delete, sender=DynamicStorage)
def prevent_accidental_storage_deletion(sender, instance, **kwargs):
    # A storage must not be deleted if it is the default storage
    # A storage must not be deleted if it is being used in a Folder
    if instance.default or Folder.objects.filter(storage=instance).exists():
        raise PermissionDenied


@receiver(pre_save, sender=DynamicStorage)
def prevent_saving_a_second_default_storage(sender, instance, **kwargs):
    # There cannot be another instance of type default_local
    if instance.storage_type == "default_local" and sender.objects.filter(storage_type="default_local").exists():
        raise PermissionDenied
