import logging

from django.db.models.fields.files import FieldFile, FileField

log = logging.getLogger(__name__)


__all__ = [
    "DynamicRuntimeStorageFileField",
]


class FileFieldMixin:
    """Common implementation that intercepts the pre_save method and injects the proper storage backend setup before saving a given file to the indicated backend"""

    def pre_save(self, model_instance, add):
        if getattr(self, "_storage_callable", None):
            if callable(self._storage_callable):
                self.storage = self._storage_callable(model_instance)
        return super().pre_save(model_instance, add)


class DynamicRuntimeStorageFieldFile(FieldFile):
    """FieldFile implementation for dynamically setting the storage provider for the file at runtime based on a callable passed into the field definition"""

    def __init__(self, instance, field, name):
        if getattr(field, "storage_instance_callable", None):
            storage = field.storage_instance_callable(instance)
            log.debug(f"Setting storage for this field to {storage}")
            field.storage = storage
        super().__init__(instance, field, name)


class DynamicRuntimeStorageFileField(FileFieldMixin, FileField):
    """File field implementation for dynamically setting the storage provider for the file to be stored/retrieved at runtime based on a callable passed into this field definition for the `storage` kwarg"""

    attr_class = DynamicRuntimeStorageFieldFile

    def __init__(self, *args, **kwargs):
        if "storage_instance_callable" in kwargs and kwargs.get("storage_instance_callable"):
            self.storage_instance_callable = kwargs.pop("storage_instance_callable")
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        if getattr(self, "storage_instance_callable", None):
            if callable(self.storage_instance_callable):
                self.storage = self.storage_instance_callable(model_instance)
        return super().pre_save(model_instance, add)
