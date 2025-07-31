import logging

from django.core.exceptions import PermissionDenied

from fdm.file_parser.models import MimeTypeParser
from fdm.metadata.helpers import set_metadata, set_metadata_for_relation
from fdm.metadata.models import Metadata
from fdm.uploads.models import UploadsDataset, UploadsVersion, UploadsVersionFile

__all__ = [
    "create_uploads_version_with_new_file_for_dataset",
    "create_uploads_version_with_new_metadata_for_dataset",
]

logger = logging.getLogger(__name__)


def create_uploads_version_with_new_file_for_dataset(
    dataset: UploadsDataset | None = None,
    uploaded_file: any = None,
    uploaded_using_tus: bool = False,
    original_file_name: str | None = None,
    original_file_path: str | None = None,
) -> UploadsVersion:
    file = UploadsVersionFile(
        uploaded_file=uploaded_file,
        uploaded_using_tus=uploaded_using_tus,
    )
    file.save()

    file_name = original_file_name or uploaded_file.name
    if file_name:
        set_metadata(
            assigned_to_content_type=file.get_content_type(),
            assigned_to_object_id=file.pk,
            custom_key="ORIGINAL_FILE_NAME",
            value=file_name,
            read_only=True,
        )

    if original_file_path:
        set_metadata(
            assigned_to_content_type=file.get_content_type(),
            assigned_to_object_id=file.pk,
            custom_key="ORIGINAL_FILE_PATH",
            value=original_file_path,
            read_only=True,
        )

    if not dataset:
        dataset = UploadsDataset.objects.create(
            name=file_name,
        )

    latest_version = dataset.latest_version

    uploads_version = UploadsVersion.objects.create(
        version_file=file,
        dataset=dataset,
    )

    # If there's already at least one version in this dataset apply all the metadata from that version to this new one
    if latest_version:
        set_metadata_for_relation(
            metadata_list=latest_version.metadata.all(),
            relation=uploads_version,
        )

    if dataset.is_published() and not uploads_version.is_published():
        uploads_version.publish()

    try:
        parser = MimeTypeParser(file=uploads_version.version_file)
        parser.parse(set_metadata=True)
    except Exception as e:
        logger.error(f"Retrieving the MIME type for file '{uploads_version.version_file}' failed: {e}")

    return uploads_version


def create_uploads_version_with_new_metadata_for_dataset(
    dataset: UploadsDataset | None = None,
    metadata_list: list[dict | Metadata] = None,
    retain_existing_metadata: bool = False,
) -> UploadsVersion:
    if dataset.locked and not dataset.is_locked_by_myself():
        raise PermissionDenied

    # There must be at least one uploads version in existence because of a file upload.
    # TODO: In the future it should be possible to have versions without files. We'll need to change this then.
    if not dataset.latest_version:
        raise PermissionDenied

    latest_version = dataset.latest_version
    latest_version_metadata_list = latest_version.metadata.all()

    # TODO: In the future it should be possible to have versions without files. We'll need to change this then.
    if not latest_version.version_file:
        raise PermissionDenied

    uploads_version = UploadsVersion.objects.create(
        version_file=latest_version.version_file,
        dataset=dataset,
    )

    if retain_existing_metadata and latest_version_metadata_list:
        set_metadata_for_relation(
            metadata_list=latest_version_metadata_list,
            relation=uploads_version,
        )

    if metadata_list is not None:
        set_metadata_for_relation(
            metadata_list=metadata_list,
            relation=uploads_version,
            retain_existing_metadata=True,
        )

    if dataset.is_published() and not uploads_version.is_published():
        uploads_version.publish()

    return uploads_version
