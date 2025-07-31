import logging

from django.conf import settings

from celery import shared_task

from fdm._celery import app
from fdm.core.helpers import set_request_for_user
from fdm.file_parser.models import *
from fdm.uploads.models import UploadsVersionFile

logger = logging.getLogger(__name__)


def clear_parser_task(parser_type: str, file: any) -> None:
    FileParser.objects.filter(
        parser_type=parser_type,
        file=file,
    ).delete()


def add_parser_task(parser_type: str, file: any) -> None:
    # Clear old parser task if the exact same one is being rescheduled
    clear_parser_task(
        parser_type=parser_type,
        file=file,
    )

    # Create a new parser task to avoid having old errors lying around
    FileParser.objects.create(
        parser_type=parser_type,
        file=file,
        status=FileParser.Status.SCHEDULED,
    )


@shared_task
def determine_tasks_for_files():
    files = UploadsVersionFile.objects.filter(
        status=UploadsVersionFile.Status.SCHEDULED,
    ).exclude(
        uploaded_file=None,
    )

    for file in files:
        # set request user to user that last updated the file so last_modified_by is automatically set correctly
        set_request_for_user(file.last_modified_by)
        check_tasks_for_file(file)
        file.status = UploadsVersionFile.Status.IN_PROGRESS
        file.save()


def check_tasks_for_file(file: UploadsVersionFile):
    check_calculate_checksum(file, FileParser.Type.CHECKSUM_SHA256)
    check_extract_exif_data(file)
    check_extract_file_information(file)


@shared_task
def update_status_for_files():
    files = UploadsVersionFile.objects.filter(
        status=UploadsVersionFile.Status.IN_PROGRESS,
    )

    for file in files:
        # set request user to user that last updated the file so last_modified_by is automatically set correctly
        set_request_for_user(file.last_modified_by)
        total_tasks_for_file = FileParser.objects.filter(
            file=file,
        )

        failed_tasks_for_file = total_tasks_for_file.filter(
            status=FileParser.Status.ERROR,
        )

        finished_tasks_for_file = total_tasks_for_file.filter(
            status=FileParser.Status.FINISHED,
        )

        if failed_tasks_for_file.count():
            file.status = UploadsVersionFile.Status.ERROR
            file.save()
        elif total_tasks_for_file.count() == finished_tasks_for_file.count():
            file.status = UploadsVersionFile.Status.FINISHED
            file.save()


def check_calculate_checksum(file: UploadsVersionFile, parser_type: str):
    # set request user to user that last updated the file so last_modified_by is automatically set correctly
    set_request_for_user(file.last_modified_by)

    add_parser_task(
        parser_type=parser_type,
        file=file,
    )

    logger.info(f"File '{file}' needs '{parser_type}' task")


@shared_task
def calculate_checksum(parser_type: str):
    generic_parser_task(
        parser_type=parser_type,
        parser_class=ChecksumParser,
        parser_args=dict(
            algorithm=parser_type,
            set_metadata=True,
        ),
    )


def check_extract_exif_data(file: UploadsVersionFile):
    parser_type = FileParser.Type.EXIF_DATA

    if ExifParser(file).check_eligible_mime_type():
        # set request user to user that last updated the file so last_modified_by is automatically set correctly
        set_request_for_user(file.last_modified_by)

        add_parser_task(
            parser_type=parser_type,
            file=file,
        )

        logger.info(f"File '{file}' needs '{parser_type}' task")


@shared_task
def extract_exif_data():
    generic_parser_task(
        parser_type=FileParser.Type.EXIF_DATA,
        parser_class=ExifParser,
        parser_args=dict(
            set_metadata=True,
        ),
    )


def check_extract_file_information(file: UploadsVersionFile):
    parser_type = FileParser.Type.FILE_INFORMATION

    # set request user to user that last updated the file so last_modified_by is automatically set correctly
    set_request_for_user(file.last_modified_by)

    add_parser_task(
        parser_type=parser_type,
        file=file,
    )

    logger.info(f"File '{file}' needs '{parser_type}' task")


@shared_task
def extract_file_information():
    generic_parser_task(
        parser_type=FileParser.Type.FILE_INFORMATION,
        parser_class=FileInformationParser,
        parser_args=dict(
            set_metadata=True,
        ),
    )


def generic_parser_task(parser_type, parser_class, parser_args):
    tasks = FileParser.objects.filter(
        parser_type=parser_type,
        status=FileParser.Status.SCHEDULED,
    )[: settings.CELERY_MAX_FILE_PARSER_TASKS_PER_INTERVAL]

    for task in tasks:
        # set request user to user that last updated the file so last_modified_by is automatically set correctly
        set_request_for_user(task.file.last_modified_by)

        task.status = FileParser.Status.IN_PROGRESS
        task.save()

        try:
            parser_class(task.file).parse(**parser_args)

            task.status = FileParser.Status.FINISHED

            logger.info(f"Task '{parser_type}' for file '{task.file}' succeeded")
        except Exception as e:
            task.status = FileParser.Status.ERROR

            task.file.status = UploadsVersionFile.Status.ERROR
            task.file.save()

            logger.error(f"Task '{parser_type}' for file '{task.file}' failed: {e}")
        finally:
            task.save()
