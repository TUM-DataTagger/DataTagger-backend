import logging

from celery import shared_task

from fdm._celery import app
from fdm.metadata.models import MetadataTemplate

logger = logging.getLogger(__name__)


@shared_task
def remove_expired_locks():
    metadata_templates = MetadataTemplate.objects.filter(
        locked=True,
    )

    for metadata_template in metadata_templates:
        try:
            metadata_template.remove_expired_lock()
        except Exception as e:
            logger.error(f"Task 'remove_expired_lock' for metadata template '{metadata_template}' failed: {e}")
