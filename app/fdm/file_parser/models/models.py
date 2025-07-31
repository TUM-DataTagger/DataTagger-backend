import hashlib
import logging
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

import magic
from PIL import Image
from PIL.ExifTags import TAGS

from fdm.core.models import BaseModel, TimestampMixin
from fdm.metadata.helpers import set_metadata
from fdm.metadata.models import Metadata
from fdm.uploads.models import UploadsVersionFile

__all__ = [
    "FileParser",
    "ChecksumParser",
    "ExifParser",
    "MimeTypeParser",
    "FileInformationParser",
]

logger = logging.getLogger(__name__)


class FileParser(BaseModel, TimestampMixin):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        IN_PROGRESS = "IN_PROGRESS", _("In progress")
        ERROR = "ERROR", _("Error")
        FINISHED = "FINISHED", _("Finished")

    class Type(models.TextChoices):
        CHECKSUM_SHA256 = "CHECKSUM_SHA256", _("Checksum SHA256")
        EXIF_DATA = "EXIF_DATA", _("EXIF data")
        MIME_TYPE = "MIME_TYPE", _("MIME type")
        FILE_INFORMATION = "FILE_INFORMATION", _("File information")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    parser_type = models.CharField(
        max_length=64,
        choices=Type.choices,
    )

    file = models.ForeignKey(
        UploadsVersionFile,
        related_name="file_parser",
        on_delete=models.CASCADE,
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )

    def __str__(self):
        return f"{self.parser_type} for {self.file}"


class ChecksumParser:
    file: UploadsVersionFile

    def __init__(self, file: UploadsVersionFile):
        self.file = file

    def parse(self, algorithm: str = FileParser.Type.CHECKSUM_SHA256, set_metadata: bool = False):
        if algorithm == FileParser.Type.CHECKSUM_SHA256:
            hasher = hashlib.sha256()
        else:
            raise NotImplementedError(_("Hash algorithm not implemented."))

        try:
            checksum = self._calculate_checksum(hasher)

            if set_metadata:
                self.set_metadata(
                    algorithm=algorithm,
                    checksum=checksum,
                )

            return checksum
        except Exception as e:
            logger.error(f"Could not retrieve checksum from file {self.file}: {e}")
            return None

    def _calculate_checksum(self, hasher) -> str:
        with self.file.uploaded_file.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def set_metadata(self, algorithm: str, checksum: str):
        Metadata.objects.filter(
            assigned_to_content_type=self.file.get_content_type(),
            assigned_to_object_id=self.file.pk,
            custom_key=algorithm,
        ).delete()

        set_metadata(
            assigned_to_content_type=self.file.get_content_type(),
            assigned_to_object_id=self.file.pk,
            custom_key=algorithm,
            value=checksum,
            read_only=True,
        )


class ExifParser:
    file: UploadsVersionFile

    allowed_mime_types = [
        "image/heic",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
    ]

    def __init__(self, file: UploadsVersionFile):
        self.file = file

    def parse(self, set_metadata: bool = False):
        if not self.check_eligible_mime_type():
            return {}

        exif_data = self._get_exif_data()

        if set_metadata:
            self.set_metadata(
                exif_data=exif_data,
            )

        return exif_data

    def get_mime_type(self) -> str:
        try:
            return magic.from_file(self.file.uploaded_file.path, mime=True)
        except Exception as e:
            logger.error(f"Could not retrieve MIME type from file {self.file}: {e}")
            return ""

    def check_eligible_mime_type(self) -> bool:
        return self.get_mime_type() in self.allowed_mime_types

    def _get_exif_data(self) -> dict:
        try:
            with Image.open(self.file.uploaded_file.path) as image_file:
                exif_data = image_file.getexif()

                exif_table = {}
                for exif_key, exif_value in exif_data.items():
                    exif_tag = TAGS.get(exif_key)
                    exif_table[exif_tag] = exif_value

                return exif_table
        except Exception as e:
            logger.error(f"Could not retrieve EXIF data from file {self.file}: {e}")
            return {}

    def set_metadata(self, exif_data: dict):
        Metadata.objects.filter(
            assigned_to_content_type=self.file.get_content_type(),
            assigned_to_object_id=self.file.pk,
            custom_key__startswith="EXIF_",
        ).delete()

        for item_key, item_value in exif_data.items():
            set_metadata(
                assigned_to_content_type=self.file.get_content_type(),
                assigned_to_object_id=self.file.pk,
                custom_key=f"EXIF_{item_key.upper()}",
                value=item_value,
                read_only=True,
            )


class MimeTypeParser:
    file: UploadsVersionFile

    def __init__(self, file: UploadsVersionFile):
        self.file = file

    def parse(self, set_metadata: bool = False):
        mime_type = self.get_mime_type()

        if set_metadata:
            self.set_metadata(
                mime_type=mime_type,
            )

        return mime_type

    def get_mime_type(self) -> str:
        return magic.from_file(self.file.uploaded_file.path, mime=True)

    def set_metadata(self, mime_type: str):
        Metadata.objects.filter(
            assigned_to_content_type=self.file.get_content_type(),
            assigned_to_object_id=self.file.pk,
            custom_key="MIME_TYPE",
        ).delete()

        set_metadata(
            assigned_to_content_type=self.file.get_content_type(),
            assigned_to_object_id=self.file.pk,
            custom_key="MIME_TYPE",
            value=mime_type,
            read_only=True,
        )


class FileInformationParser:
    file: UploadsVersionFile

    def __init__(self, file: UploadsVersionFile):
        self.file = file

    def parse(self, set_metadata: bool = False):
        information = dict(
            file_name=self.file.name,
            file_size=self.file.file_size,
            file_relative_path=self.file.relative_path,
        )

        if set_metadata:
            self.set_metadata(
                information=information,
            )

        return information

    def set_metadata(self, information: dict):
        Metadata.objects.filter(
            assigned_to_content_type=self.file.get_content_type(),
            assigned_to_object_id=self.file.pk,
            custom_key__in=[k.upper() for k in list(information.keys())],
        ).delete()

        for key, value in information.items():
            set_metadata(
                assigned_to_content_type=self.file.get_content_type(),
                assigned_to_object_id=self.file.pk,
                custom_key=key.upper(),
                value=value,
                read_only=True,
            )
