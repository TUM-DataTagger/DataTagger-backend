import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from celery import shared_task

from fdm._celery import app
from fdm.core.helpers import set_request_for_user
from fdm.uploads.models import UploadsDataset, UploadsVersion, UploadsVersionFile

__all__ = [
    "check_metadata_completeness",
    "remove_expired_locks",
    "remove_expired_dataset_drafts",
    "move_files",
]

logger = logging.getLogger(__name__)


@shared_task
def check_metadata_completeness():
    uploads_versions = UploadsVersion.objects.filter(
        status=UploadsVersion.Status.SCHEDULED,
    )

    for uploads_version in uploads_versions:
        # set request user to user that last updated the version so last_modified_by is automatically set correctly
        set_request_for_user(uploads_version.last_modified_by)

        try:
            uploads_version.status = UploadsVersion.Status.IN_PROGRESS
            uploads_version.save()

            uploads_version.metadata_is_complete = uploads_version.check_metadata_completeness()
            uploads_version.save()

            uploads_version.status = UploadsVersion.Status.FINISHED
            uploads_version.save()

            logger.info(f"Task 'check_metadata_completeness' for uploads version '{uploads_version}' succeeded")
        except PermissionDenied:
            logger.error(
                f"Task 'check_metadata_completeness' for uploads version '{uploads_version}' failed because of a "
                "permission error",
            )
        except Exception as e:
            uploads_version.status = UploadsVersion.Status.ERROR
            uploads_version.save()

            logger.error(f"Task 'check_metadata_completeness' for uploads version '{uploads_version}' failed: {e}")


@shared_task
def remove_expired_locks():
    datasets = UploadsDataset.objects.filter(
        locked=True,
    )

    for dataset in datasets:
        try:
            dataset.remove_expired_lock()
        except Exception as e:
            logger.error(f"Task 'remove_expired_lock' for dataset '{dataset}' failed: {e}")


@shared_task
def remove_expired_dataset_drafts():
    datasets = UploadsDataset.objects.filter(
        publication_date__isnull=True,
        expiry_date__lt=timezone.now(),
    )

    for dataset in datasets:
        try:
            # set request user to user that created the dataset, so we can actually delete it
            set_request_for_user(dataset.created_by)
            dataset.delete()
        except Exception as e:
            logger.error(f"Task 'remove_expired_dataset_drafts' for dataset '{dataset}' failed: {e}")


@shared_task
def move_files():
    # only move files after all the parsing is done
    version_files = UploadsVersionFile.objects.filter(
        storage_relocating=UploadsVersionFile.Status.SCHEDULED,
        status=UploadsVersionFile.Status.FINISHED,
    )

    for version_file in version_files:
        set_request_for_user(version_file.last_modified_by)
        version_file.move_file()
