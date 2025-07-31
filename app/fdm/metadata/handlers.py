from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from fdm.metadata.models import Metadata, MetadataField, MetadataTemplateField


@receiver(pre_save, sender=MetadataField)
def pre_save_metadata_field_update_field_type(sender, instance, *args, **kwargs):
    # If the metadata field is created then we don't need to check anything
    if instance.pk is None:
        return

    # Get the old value for this metadata field if it already exists, else abort
    try:
        old_metadata_field_data = MetadataField.objects.get(pk=instance.pk)
    except MetadataField.DoesNotExist:
        return

    # Check if the field type has been changed for this metadata field
    if old_metadata_field_data.field_type == instance.field_type:
        return

    if instance.metadata.exists() or instance.metadata_template_fields.exists():
        raise PermissionDenied


@receiver(pre_delete, sender=MetadataField)
def pre_delete_metadata_field(sender, instance, **kwargs):
    if instance.metadata.exists() or instance.metadata_template_fields.exists():
        raise PermissionDenied


@receiver(pre_save, sender=Metadata)
def pre_save_metadata_update_field_type(sender, instance, *args, **kwargs):
    if instance.field:
        instance.field_type = instance.field.field_type


@receiver(post_save, sender=Metadata)
def post_save_metadata_update_dataset_display_name(sender, instance, *args, **kwargs):
    if hasattr(instance.assigned_to_content_object, "uploads_versions"):
        for uploads_version in instance.assigned_to_content_object.uploads_versions.all():
            uploads_version.dataset.set_display_name()


@receiver(post_delete, sender=Metadata)
def post_delete_metadata_update_dataset_display_name(sender, instance, *args, **kwargs):
    if hasattr(instance.assigned_to_content_object, "uploads_versions"):
        for uploads_version in instance.assigned_to_content_object.uploads_versions.all():
            uploads_version.dataset.set_display_name()


@receiver(pre_save, sender=Metadata)
def pre_save_metadata_config(sender, instance, *args, **kwargs):
    if not instance.config:
        instance.config = {}


@receiver(pre_save, sender=MetadataTemplateField)
def pre_save_metadata_template_field_config(sender, instance, *args, **kwargs):
    if not instance.config:
        instance.config = {}
