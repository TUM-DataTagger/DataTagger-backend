import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from fdm.core.helpers import clean_assigned_content_type
from fdm.core.models import BaseModel, ByUserMixin, LockMixin, TimestampMixin
from fdm.metadata.enums import MetadataFieldType

__all__ = [
    "MetadataField",
    "Metadata",
    "MetadataTemplate",
    "MetadataTemplateField",
]


class MetadataField(BaseModel, TimestampMixin, ByUserMixin):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    key = models.CharField(
        max_length=128,
        unique=True,
    )

    field_type = models.CharField(
        max_length=16,
        choices=MetadataFieldType.choices,
        default=MetadataFieldType.TEXT,
    )

    read_only = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return f"{self.key} ({self.field_type})"


class Metadata(BaseModel, TimestampMixin, ByUserMixin):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    field = models.ForeignKey(
        MetadataField,
        blank=True,
        null=True,
        related_name="metadata",
        on_delete=models.CASCADE,
    )

    custom_key = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    field_type = models.CharField(
        max_length=16,
        choices=MetadataFieldType.choices,
        default=MetadataFieldType.TEXT,
    )

    read_only = models.BooleanField(
        default=False,
    )

    value = models.JSONField(
        blank=True,
        null=False,
        default=dict,
    )

    config = models.JSONField(
        blank=True,
        null=False,
        default=dict,
    )

    metadata_template_field = models.ForeignKey(
        "MetadataTemplateField",
        blank=True,
        null=True,
        related_name="metadata",
        on_delete=models.SET_NULL,
    )

    assigned_to_content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    assigned_to_object_id = models.UUIDField(
        blank=True,
        null=True,
    )

    assigned_to_content_object = GenericForeignKey(
        ct_field="assigned_to_content_type",
        fk_field="assigned_to_object_id",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "assigned_to_content_type",
                    "assigned_to_object_id",
                ],
            ),
        ]

    def clean(self):
        if self.field and self.custom_key:
            raise ValidationError(_("You must not link a metadata field and declare a custom key together."))

        if not self.field and not self.custom_key:
            raise ValidationError(_("You must either link a metadata field or declare a custom key."))

        if self.get_value() is not None:
            from fdm.metadata.helpers import validate_metadata_value

            validate_metadata_value(
                field=self.field,
                field_type=self.field_type,
                custom_key=self.custom_key,
                value=self.get_value(),
                config=self.config,
            )

        from fdm.folders.models import Folder
        from fdm.projects.models import Project
        from fdm.uploads.models import UploadsVersion, UploadsVersionFile

        clean_assigned_content_type(
            assigned_to_content_type=self.assigned_to_content_type,
            assigned_to_object_id=self.assigned_to_object_id,
            allowed_content_models=[
                Project,
                Folder,
                UploadsVersion,
                UploadsVersionFile,
            ],
        )

    def save(self, *args, **kwargs):
        if self.field and self.field.read_only:
            self.read_only = True

        super().save(*args, **kwargs)

    def set_value(self, value):
        from fdm.metadata.helpers import get_metadata_structure_for_type

        self.value = get_metadata_structure_for_type(self.field_type, value)
        self.save()

    def get_value(self):
        from fdm.metadata.helpers import get_metadata_value_for_type

        return get_metadata_value_for_type(self.field_type, self.value)

    def __str__(self):
        return f"{self.assigned_to_content_type} ({self.assigned_to_object_id}): {self.custom_key or self.field.key}"


class MetadataTemplate(BaseModel, TimestampMixin, ByUserMixin, LockMixin):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
    )

    assigned_to_content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    assigned_to_object_id = models.UUIDField(
        blank=True,
        null=True,
    )

    assigned_to_content_object = GenericForeignKey(
        ct_field="assigned_to_content_type",
        fk_field="assigned_to_object_id",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "assigned_to_content_type",
                    "assigned_to_object_id",
                ],
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        from fdm.folders.models import Folder
        from fdm.projects.models import Project

        clean_assigned_content_type(
            assigned_to_content_type=self.assigned_to_content_type,
            assigned_to_object_id=self.assigned_to_object_id,
            allowed_content_models=[
                Project,
                Folder,
            ],
        )


class MetadataTemplateField(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    metadata_template = models.ForeignKey(
        MetadataTemplate,
        blank=False,
        null=False,
        related_name="metadata_template_fields",
        on_delete=models.CASCADE,
    )

    field = models.ForeignKey(
        MetadataField,
        blank=True,
        null=True,
        related_name="metadata_template_fields",
        on_delete=models.CASCADE,
    )

    custom_key = models.CharField(
        max_length=128,
        blank=True,
        null=True,
    )

    field_type = models.CharField(
        max_length=16,
        choices=MetadataFieldType.choices,
        default=MetadataFieldType.TEXT,
    )

    value = models.JSONField(
        blank=True,
        null=False,
        default=dict,
    )

    config = models.JSONField(
        blank=True,
        null=False,
        default=dict,
    )

    mandatory = models.BooleanField(
        default=False,
    )

    def clean(self):
        if self.field and self.custom_key:
            raise ValidationError(_("You must not link a metadata field and declare a custom key together."))

        if not self.field and not self.custom_key:
            raise ValidationError(_("You must either link a metadata field or declare a custom key."))

        if self.get_value() is not None:
            from fdm.metadata.helpers import validate_metadata_value

            validate_metadata_value(
                field=self.field,
                field_type=self.field_type,
                custom_key=self.custom_key,
                value=self.get_value(),
                config=self.config,
            )

    def set_value(self, value):
        from fdm.metadata.helpers import get_metadata_structure_for_type

        self.value = get_metadata_structure_for_type(self.field_type, value)
        self.save()

    def get_value(self):
        from fdm.metadata.helpers import get_metadata_value_for_type

        return get_metadata_value_for_type(self.field_type, self.value)

    def __str__(self):
        return f"{self.metadata_template}: {self.custom_key or self.field}"
