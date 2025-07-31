import logging
import os
import uuid

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_userforeignkey.request import get_current_user

from fdm.core.models import BaseModel, ByUserMixin, LockMixin, TimestampMixin
from fdm.folders.models import Folder
from fdm.metadata.helpers import set_metadata_for_relation
from fdm.metadata.models import Metadata, MetadataTemplateField
from fdm.storages.fields import DynamicRuntimeStorageFileField
from fdm.storages.models.mappings import STORAGE_PROVIDER_MAP
from fdm.uploads.models.managers import UploadsDatasetManager, UploadsVersionManager

__all__ = [
    "get_storage",
    "get_upload_to_path",
    "UploadsDataset",
    "UploadsVersion",
    "UploadsVersionFile",
]

logger = logging.getLogger(__name__)


def get_storage(instance):
    """Get storage instance with proper fallback"""
    if instance.is_published():
        storage = instance.get_storage()
        if storage:
            return storage.storage_backend
        # Fallback for published files uses "local" prefix
        create_class = STORAGE_PROVIDER_MAP["default_local"]["class"]
        create_kwargs = {"path_prefix": "local"}
    else:
        # Unpublished files always use "temp" prefix
        create_class = STORAGE_PROVIDER_MAP["default_local"]["class"]
        create_kwargs = {"path_prefix": "temp"}

    return create_class(**create_kwargs)


def get_upload_to_path(instance, filename):
    if instance.is_published():
        storage = instance.get_storage()
        return storage.get_upload_to_path(instance, filename)
    else:
        now = timezone.now()
        user = get_current_user()
        return now.strftime(f"temp/{user.id}/%Y/%m/%d/{filename}")


class UploadsDataset(BaseModel, TimestampMixin, ByUserMixin, LockMixin):
    objects = UploadsDatasetManager()

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    display_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    folder = models.ForeignKey(
        Folder,
        blank=True,
        null=True,
        related_name="uploads_dataset",
        on_delete=models.CASCADE,
    )

    publication_date = models.DateTimeField(
        verbose_name=_("Publication date"),
        blank=True,
        null=True,
    )

    expiry_date = models.DateTimeField(
        verbose_name=_("Expiry date"),
        blank=True,
        null=True,
    )

    @property
    def get_sorted_versions(self):
        return self.uploads_versions.order_by("-creation_date")

    @property
    def get_sorted_published_versions(self):
        return self.get_sorted_versions.exclude(
            publication_date__isnull=True,
        )

    @property
    def latest_version(self):
        return self.get_sorted_versions.first()

    @property
    def is_expired(self) -> bool:
        return bool(self.expiry_date and self.expiry_date < timezone.now())

    def latest_version_name(self) -> str | None:
        if self.latest_version and self.latest_version.version_file:
            try:
                original_filename = self.latest_version.version_file.metadata.get(custom_key="FILE_NAME")
                return original_filename.get_value()
            except Metadata.DoesNotExist:
                return self.latest_version.version_file.name

        return None

    def get_display_name(self):
        return f"{self.name or self.latest_version_name() or self.id}"

    def set_display_name(self):
        self.display_name = self.get_display_name()
        self.save()

    def is_published(self) -> bool:
        return self.publication_date is not None

    is_published.boolean = True
    is_published.short_description = "Is published"

    def get_all_metadata_template_fields(self):
        metadata_list = []

        if self.folder.project and self.folder.project.metadata_template:
            metadata_list += self.folder.project.metadata_template.metadata_template_fields.all()

        if self.folder.metadata_template:
            metadata_list += self.folder.metadata_template.metadata_template_fields.all()

        return metadata_list

    def publish(self, folder: Folder | str = None):
        from fdm.uploads.helpers import create_uploads_version_with_new_metadata_for_dataset

        if not folder and not self.folder:
            raise ValidationError(_("You can't publish a dataset without a folder."))

        if self.locked and not self.is_locked_by_myself():
            raise PermissionDenied(_("You must not edit an element which has been locked by another user."))

        if self.is_published():
            raise PermissionDenied(_("This dataset has already been published."))

        if folder:
            self.folder_id = folder.pk if isinstance(folder, Folder) else folder

        self.expiry_date = None
        self.publication_date = timezone.now()
        self.save()

        # When the dataset gets published and the folder (or the project of the folder) it gets published into has an
        # active metadata template assignment then create a new version and automatically add all the template fields.
        metadata_list = self.get_all_metadata_template_fields()
        if metadata_list:
            try:
                create_uploads_version_with_new_metadata_for_dataset(
                    dataset=self,
                    metadata_list=metadata_list,
                    retain_existing_metadata=True,
                )
            except Exception as e:
                logger.error(f"Could not apply metadata from metadata template fields to uploads dataset {self}: {e}")

        for uploads_version in self.uploads_versions.order_by("creation_date"):
            if not uploads_version.is_published():
                uploads_version.publish()

    def restore_version(self, uploads_version: any = None):
        if not uploads_version:
            raise ValidationError(_("You can't restore a specific uploads version without providing a primary key."))

        if self.locked and not self.is_locked_by_myself():
            raise PermissionDenied(_("You must not edit an element which has been locked by another user."))

        if self.uploads_versions.count() < 2:
            raise PermissionDenied(
                _("A dataset must have at least two versions before you can restore a specific version."),
            )

        if isinstance(uploads_version, str):
            try:
                uploads_version = UploadsVersion.objects.get(
                    pk=uploads_version,
                )
            except UploadsVersion.DoesNotExist:
                raise ValidationError(_("The version you want to restore does not exist."))

        if self.latest_version == uploads_version:
            raise PermissionDenied(
                _("You can't restore the latest version of a dataset."),
            )

        if uploads_version.dataset != self:
            raise PermissionDenied(_("The version you want to restore is not part of the dataset."))

        # TODO: In the future it should be possible to have versions without files. We'll need to change this then.
        if not uploads_version.version_file:
            raise PermissionDenied(_("The version you want to restore has no file attached to it."))

        new_uploads_version = UploadsVersion.objects.create(
            version_file=uploads_version.version_file,
            dataset=self,
        )

        if uploads_version.metadata.exists():
            set_metadata_for_relation(
                metadata_list=uploads_version.metadata.all(),
                relation=new_uploads_version,
            )

        if self.is_published():
            new_uploads_version.publish()

        return new_uploads_version

    def __str__(self):
        return f"{self.display_name or self.name or self.id}"

    def delete(self, *args, **kwargs):
        for uploads_version in self.uploads_versions.all():
            uploads_version.delete()

        super().delete(*args, **kwargs)


class UploadsVersionFile(BaseModel, TimestampMixin, ByUserMixin):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        PROCESSED = "PROCESSED", _("Processed")
        IN_PROGRESS = "IN_PROGRESS", _("In progress")
        ERROR = "ERROR", _("Error")
        FINISHED = "FINISHED", _("Finished")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    uploaded_file = DynamicRuntimeStorageFileField(
        max_length=4096,
        upload_to=get_upload_to_path,
        storage_instance_callable=get_storage,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )

    uploaded_using_tus = models.BooleanField(
        default=False,
    )

    is_referenced = models.BooleanField(
        default=False,
    )

    storage_relocating = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.FINISHED,
    )

    publication_date = models.DateTimeField(
        verbose_name=_("Publication date"),
        blank=True,
        null=True,
    )

    metadata = GenericRelation(
        Metadata,
        content_type_field="assigned_to_content_type",
        object_id_field="assigned_to_object_id",
    )

    @property
    def file_size(self) -> int:
        return self.uploaded_file.size

    @property
    def absolute_path(self) -> str:
        return os.path.dirname(self.uploaded_file.path)

    @property
    def relative_path(self) -> str:
        return os.path.dirname(self.uploaded_file.name)

    @property
    def name(self) -> str:
        return os.path.basename(self.uploaded_file.name)

    def is_published(self) -> bool:
        return self.publication_date is not None

    is_published.boolean = True
    is_published.short_description = "Is published"

    def publish(self):
        if self.is_published():
            raise PermissionDenied(_("This version file has already been published."))

        self.publication_date = timezone.now()
        self.storage_relocating = self.Status.SCHEDULED
        self.save()

    def move_file(self):
        from fdm.uploads.handlers import move_storage_file

        self.storage_relocating = self.Status.IN_PROGRESS
        self.save()

        try:
            move_storage_file(self.get_storage(), self)
            self.storage_relocating = self.Status.FINISHED
            if not self.status == self.Status.FINISHED:
                self.status = self.Status.SCHEDULED
        except Exception as e:
            self.storage_relocating = self.Status.ERROR
            logger.error(f"Failed to move file to new storage location: {e}")

        self.save()

    def reset_status(self):
        self.status = self.Status.SCHEDULED
        self.save()

    def get_folder(self):
        uploads_version = self.uploads_versions.first()

        if uploads_version and uploads_version.dataset:
            return uploads_version.dataset.folder

        return None

    def get_project(self):
        folder = self.get_folder()

        if folder:
            return folder.project

        return None

    def get_storage(self):
        folder = self.get_folder()

        if folder:
            return folder.storage

        return None

    def __str__(self):
        return f"{self.name or self.id}"

    def delete(self, *args, **kwargs):
        if self.uploaded_file and os.path.exists(self.uploaded_file.path):
            os.remove(self.uploaded_file.path)

        super().delete(*args, **kwargs)


class UploadsVersion(BaseModel, TimestampMixin, ByUserMixin):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        IN_PROGRESS = "IN_PROGRESS", _("In progress")
        ERROR = "ERROR", _("Error")
        FINISHED = "FINISHED", _("Finished")

    objects = UploadsVersionManager()

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    dataset = models.ForeignKey(
        UploadsDataset,
        blank=True,
        null=True,
        related_name="uploads_versions",
        on_delete=models.CASCADE,
    )

    version_file = models.ForeignKey(
        UploadsVersionFile,
        blank=True,
        null=True,
        related_name="uploads_versions",
        on_delete=models.CASCADE,
    )

    publication_date = models.DateTimeField(
        verbose_name=_("Publication date"),
        blank=True,
        null=True,
    )

    metadata = GenericRelation(
        Metadata,
        content_type_field="assigned_to_content_type",
        object_id_field="assigned_to_object_id",
    )

    metadata_is_complete = models.BooleanField(
        default=True,
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )

    @property
    def locked(self):
        return self.dataset.locked

    @property
    def locked_by(self):
        return self.dataset.locked_by

    @property
    def locked_at(self):
        return self.dataset.locked_at

    def is_published(self) -> bool:
        return self.publication_date is not None

    is_published.boolean = True
    is_published.short_description = "Is published"

    def is_latest_version(self) -> bool:
        return self.dataset and self.dataset.latest_version.pk == self.pk

    is_latest_version.boolean = True
    is_latest_version.short_description = "Is latest version in dataset"

    def check_metadata_completeness(self) -> bool:
        if self.dataset.folder and self.dataset.folder.metadata_template:
            metadata_template_fields = MetadataTemplateField.objects.filter(
                metadata_template=self.dataset.folder.metadata_template,
                mandatory=True,
            )

            if not metadata_template_fields.exists():
                return True

            metadata = {m.custom_key or str(m.field.pk): m.value for m in list(self.metadata.all())}

            for field in metadata_template_fields:
                if not metadata.get(field.custom_key or str(field.field.pk), None):
                    return False

        return True

    def get_all_metadata(self):
        metadata = list(self.metadata.all())

        try:
            if self.version_file:
                metadata += list(self.version_file.metadata.all())

                # TODO: In the future it should be possible to have versions without files. We'll need to change this then.
                version_file_folder = self.version_file.get_folder()
                if version_file_folder:
                    metadata += list(version_file_folder.metadata.all())

                # TODO: In the future it should be possible to have versions without files. We'll need to change this then.
                version_file_project = self.version_file.get_project()
                if version_file_project:
                    metadata += list(version_file_project.metadata.all())
        except UploadsVersionFile.DoesNotExist:
            pass

        return metadata

    def publish(self):
        if self.dataset.locked and not self.dataset.is_locked_by_myself():
            raise PermissionDenied(_("You must not edit an element which has been locked by another user."))

        if self.is_published():
            raise PermissionDenied(_("This version has already been published."))

        self.publication_date = timezone.now()
        self.save()

        if not self.version_file.is_published():
            self.version_file.publish()

    def reset_status(self):
        self.status = self.Status.SCHEDULED
        self.save()

    def __str__(self):
        return f"{self.dataset}: {self.name or self.id}"

    def delete(self, *args, **kwargs):
        try:
            self.version_file.delete()
        except UploadsVersionFile.DoesNotExist:
            pass

        super().delete(*args, **kwargs)
