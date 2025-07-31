import logging

from celery import shared_task

from fdm._celery import app
from fdm.folders.models import Folder

logger = logging.getLogger(__name__)


@shared_task
def remove_expired_locks():
    folders = Folder.objects.filter(
        locked=True,
    )

    for folder in folders:
        try:
            folder.remove_expired_lock()
        except Exception as e:
            logger.error(f"Task 'remove_expired_lock' for folder '{folder}' failed: {e}")
