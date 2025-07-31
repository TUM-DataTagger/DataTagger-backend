import logging
import os
import shutil

from django.conf import settings
from django.core.files.storage import FileSystemStorage

__all__ = [
    "DefaultLocalFileSystemStorage",
    "PrivateDSSLocalFileSystemStorage",
]


logger = logging.getLogger(__name__)


class DefaultLocalFileSystemStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, path_prefix=""):
        self.path_prefix = path_prefix
        super().__init__(
            location=location or os.path.join(settings.MEDIA_ROOT),
            base_url=base_url or settings.MEDIA_URL,
        )

    def get_upload_to_path(self, instance, filename):
        folder = instance.get_folder()
        return self.get_available_name(
            name=os.path.join(
                self.location,
                self.path_prefix,
                str(folder.project.pk),
                str(folder.pk),
                filename,
            ),
            max_length=255,
        )

    def move_file(self, version_file):
        from fdm.uploads.models import get_upload_to_path

        old_file_path = version_file.uploaded_file.name
        new_file_path = get_upload_to_path(version_file, version_file.name)
        new_file_path = new_file_path.replace(self.location, "", 1).lstrip("/")

        if os.path.dirname(old_file_path) == os.path.dirname(new_file_path):
            return False, old_file_path

        new_absolute_file_path = os.path.join(self.location, new_file_path)
        new_dir_name = os.path.dirname(new_absolute_file_path)

        if not os.path.exists(new_dir_name):
            os.makedirs(new_dir_name)

        if os.path.exists(version_file.uploaded_file.path) and os.path.exists(new_dir_name):
            # Use shutil.move for cross-device moves
            shutil.move(
                str(version_file.uploaded_file.path),
                str(new_absolute_file_path),
                copy_function=shutil.copy,
            )
            return True, new_file_path
        else:
            return False, version_file.uploaded_file.path


class PrivateDSSLocalFileSystemStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, path_prefix=""):
        self.path_prefix = path_prefix
        self.temp_storage = DefaultLocalFileSystemStorage()
        super().__init__(
            location=location,
            base_url=base_url or settings.MEDIA_URL,
        )

    def path(self, name):
        """Return the absolute filesystem path for temp or private storage"""
        if name and name.startswith("temp/") or name.startswith("local/"):
            return self.temp_storage.path(name)
        return os.path.join(self.location, name)

    def get_upload_to_path(self, instance, filename):
        folder = instance.get_folder()

        if instance.is_referenced:
            return self.get_available_name(
                name=os.path.join(
                    settings.PRIVATE_DSS_MOUNT_PATH,
                    folder.storage.local_private_dss_path,
                    instance.filepath.lstrip("/"),
                ),
                max_length=255,
            )

        if not instance.is_published():
            return self.temp_storage.get_upload_to_path(instance, filename)

        return self.get_available_name(
            name=os.path.join(
                self.location,
                self.path_prefix,
                str(folder.project.pk),
                str(folder.pk),
                filename,
            ),
            max_length=255,
        )

    def move_file(self, version_file):
        from fdm.uploads.models import get_upload_to_path

        old_absolute_path = version_file.uploaded_file.path
        new_file_path = get_upload_to_path(version_file, version_file.name)
        new_absolute_file_path = os.path.join(self.location, new_file_path)
        new_dir_name = os.path.dirname(new_absolute_file_path)

        if os.path.dirname(old_absolute_path) == os.path.dirname(new_absolute_file_path):
            return False, old_absolute_path

        if not os.path.exists(new_dir_name):
            os.makedirs(new_dir_name)

        if os.path.exists(old_absolute_path) and os.path.exists(new_dir_name):
            # Use shutil.move for cross-device moves
            shutil.move(
                str(old_absolute_path),
                str(new_absolute_file_path),
                copy_function=shutil.copy,
            )
            return True, new_file_path
        else:
            return False, version_file.uploaded_file.path
