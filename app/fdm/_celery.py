from django.conf import settings

from celery import Celery
from celery.schedules import crontab

app = Celery("fdm")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(settings.INSTALLED_APPS)

# Celery beat schedule
app.conf.beat_schedule = {
    "dataset_remove_expired_drafts": {
        "task": "fdm.uploads.tasks.remove_expired_dataset_drafts",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
    "dataset_remove_expired_locks": {
        "task": "fdm.uploads.tasks.remove_expired_locks",
        "schedule": 60 * 1,  # 1 minute
    },
    "file_parser_calculate_sha256_checksum": {
        "task": "fdm.file_parser.tasks.calculate_checksum",
        "args": ("CHECKSUM_SHA256",),
        "schedule": 60 * 1,  # 1 minute
    },
    "file_parser_determine_tasks_for_files": {
        "task": "fdm.file_parser.tasks.determine_tasks_for_files",
        "schedule": 60 * 1,  # 1 minute
    },
    "file_parser_extract_exif_data": {
        "task": "fdm.file_parser.tasks.extract_exif_data",
        "schedule": 60 * 1,  # 1 minute
    },
    "file_parser_extract_file_information": {
        "task": "fdm.file_parser.tasks.extract_file_information",
        "schedule": 60 * 1,  # 1 minute
    },
    "file_parser_update_status_for_files": {
        "task": "fdm.file_parser.tasks.update_status_for_files",
        "schedule": 60 * 1,  # 1 minute
    },
    "folder_remove_expired_locks": {
        "task": "fdm.folders.tasks.remove_expired_locks",
        "schedule": 60 * 1,  # 1 minute
    },
    "project_remove_expired_locks": {
        "task": "fdm.projects.tasks.remove_expired_locks",
        "schedule": 60 * 1,  # 1 minute
    },
    "metadata_template_remove_expired_locks": {
        "task": "fdm.metadata.tasks.remove_expired_locks",
        "schedule": 60 * 1,  # 1 minute
    },
    "uploads_version_check_metadata_completeness": {
        "task": "fdm.uploads.tasks.check_metadata_completeness",
        "schedule": 60 * 1,  # 1 minute
    },
    "uploads_version_file_move_files": {
        "task": "fdm.uploads.tasks.move_files",
        "schedule": 60 * 1,  # 1 minute
    },
    "check_private_dss_storages_mounting_status": {
        "task": "fdm.storages.tasks.check_private_dss_storages_mounting_status",
        "schedule": 60 * 5,  # 5 minutes
    },
    "rest_framework_tus_remove_expired_uploads": {
        "task": "fdm.rest_framework_tus.tasks.remove_expired_uploads",
        "schedule": 60 * 60,  # 1 hour
    },
}
