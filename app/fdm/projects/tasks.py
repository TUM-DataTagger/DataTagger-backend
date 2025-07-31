import logging

from celery import shared_task

from fdm._celery import app
from fdm.projects.models import Project

logger = logging.getLogger(__name__)


@shared_task
def remove_expired_locks():
    projects = Project.objects.filter(
        locked=True,
    )

    for project in projects:
        try:
            project.remove_expired_lock()
        except Exception as e:
            logger.error(f"Task 'remove_expired_lock' for project '{project}' failed: {e}")
