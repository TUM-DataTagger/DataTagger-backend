import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

import pytest

from fdm.core.helpers import set_request_for_user
from fdm.metadata.enums import MetadataFieldType
from fdm.metadata.helpers import set_metadata
from fdm.metadata.models import Metadata, MetadataField
from fdm.projects.models import Project
from fdm.storages.models import DynamicStorage
from fdm.uploads.models import UploadsDataset, UploadsVersion, UploadsVersionFile
from fdm.uploads.tasks import remove_expired_dataset_drafts

User = get_user_model()

sample_file = SimpleUploadedFile(
    "file.jpg",
    b"",
    content_type="image/jpg",
)


@pytest.mark.django_db
class TestUploadsDatasetModel:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        self.uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
        )

    def test_string_representation(self):
        """
        Ensure we get the correct string representation of a dataset.
        """
        assert str(self.uploads_dataset_1) == self.uploads_dataset_1.name

        uploads_dataset_2 = UploadsDataset.objects.create()
        assert str(uploads_dataset_2) == str(uploads_dataset_2.pk)

    def test_latest_version(self):
        """
        Ensure we get the latest version of a dataset.
        """
        uploads_version_1 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            publication_date=timezone.now(),
        )

        assert self.uploads_dataset_1.latest_version.pk == uploads_version_1.pk

        uploads_version_2 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            publication_date=timezone.now(),
        )

        assert self.uploads_dataset_1.latest_version.pk == uploads_version_2.pk

    def test_delete(self, initial_users):
        """
        Ensure we can delete a dataset as long as it has not been published.
        """
        set_request_for_user(initial_users["user_1"])

        dataset_pk = self.uploads_dataset_1.pk

        self.uploads_dataset_1.delete()
        assert not UploadsDataset.objects.filter(pk=dataset_pk).exists()

        uploads_dataset_2 = UploadsDataset.objects.create(
            name="Dataset 2",
        )
        uploads_dataset_2_pk = uploads_dataset_2.pk

        version_file = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )
        version_file_pk = version_file.pk
        version_file_path = version_file.uploaded_file.path

        uploads_version = UploadsVersion.objects.create(
            dataset=uploads_dataset_2,
            version_file=version_file,
        )
        uploads_version_pk = uploads_version.pk

        uploads_dataset_2.delete()

        assert not UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert not UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert not UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert not os.path.exists(version_file_path)

        uploads_dataset_3 = UploadsDataset.objects.create(
            name="Dataset 3",
        )
        uploads_dataset_3_pk = uploads_dataset_3.pk

        version_file = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )
        version_file_pk = version_file.pk
        version_file_path = version_file.uploaded_file.path

        uploads_version = UploadsVersion.objects.create(
            dataset=uploads_dataset_3,
            version_file=version_file,
        )
        uploads_version_pk = uploads_version.pk

        uploads_dataset_3.lock()
        uploads_dataset_3.delete()

        assert not UploadsDataset.objects.filter(pk=uploads_dataset_3_pk).exists()
        assert not UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert not UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert not os.path.exists(version_file_path)

    def test_hard_delete(self, initial_users):
        """
        Ensure we can hard delete a dataset with the appropriate permission.
        """
        user_1 = User.objects.get(pk=initial_users["user_1"].pk)
        assert user_1.can_hard_delete_datasets is False

        version_file = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=version_file,
        )

        self.uploads_dataset_1.publication_date = timezone.now()
        self.uploads_dataset_1.save()

        assert UploadsDataset.objects.count() == 1
        assert self.uploads_dataset_1.publication_date is not None
        assert UploadsVersion.objects.count() == 1
        assert UploadsVersionFile.objects.count() == 1

        with transaction.atomic():
            with pytest.raises(PermissionDenied):
                self.uploads_dataset_1.delete()

        assert UploadsDataset.objects.count() == 1
        assert self.uploads_dataset_1.publication_date is not None
        assert UploadsVersion.objects.count() == 1
        assert UploadsVersionFile.objects.count() == 1

        initial_users["user_1"].can_hard_delete_datasets = True
        initial_users["user_1"].save()

        user_1.refresh_from_db()
        assert user_1.can_hard_delete_datasets is True

        self.uploads_dataset_1.delete()

        assert UploadsDataset.objects.count() == 0
        assert UploadsVersion.objects.count() == 0
        assert UploadsVersionFile.objects.count() == 0

    def test_delete_protection(self, initial_users):
        """
        Ensure we can't delete a dataset if it has been published.
        """
        set_request_for_user(initial_users["user_1"])

        dataset_pk = self.uploads_dataset_1.pk

        self.uploads_dataset_1.publication_date = timezone.now()
        self.uploads_dataset_1.save()

        with transaction.atomic():
            with pytest.raises(PermissionDenied):
                self.uploads_dataset_1.delete()

        assert UploadsDataset.objects.filter(pk=dataset_pk).exists()

        uploads_dataset_2 = UploadsDataset.objects.create(
            name="Dataset 2",
            publication_date=timezone.now(),
        )

        version_file = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        uploads_version = UploadsVersion.objects.create(
            dataset=uploads_dataset_2,
            version_file=version_file,
        )

        dataset_pk = uploads_dataset_2.pk

        with transaction.atomic():
            with pytest.raises(PermissionDenied):
                uploads_dataset_2.delete()

        assert UploadsDataset.objects.filter(pk=dataset_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version.pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

        uploads_dataset_2.publication_date = None
        uploads_dataset_2.save()

        version_file.publish()

        with transaction.atomic():
            with pytest.raises(PermissionDenied):
                uploads_dataset_2.delete()

        assert UploadsDataset.objects.filter(pk=dataset_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version.pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

        version_file.publication_date = None
        version_file.save()

        uploads_version.publication_date = timezone.now()
        uploads_version.save()

        with transaction.atomic():
            with pytest.raises(PermissionDenied):
                uploads_dataset_2.delete()

        assert UploadsDataset.objects.filter(pk=dataset_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version.pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

        UploadsVersion.objects.create(
            dataset=uploads_dataset_2,
            version_file=version_file,
        )

        with transaction.atomic():
            with pytest.raises(PermissionDenied):
                assert version_file.delete()

        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

    def test_check_expired_draft(self, initial_users):
        """
        Ensure we can determine if a dataset in the drafts section has expired.
        """
        assert self.uploads_dataset_1.is_expired is False
        assert self.uploads_dataset_1.expiry_date is not None
        assert self.uploads_dataset_1.expiry_date > timezone.now()

        self.uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        self.uploads_dataset_1.save()

        assert self.uploads_dataset_1.is_expired is True
        assert self.uploads_dataset_1.expiry_date is not None
        assert self.uploads_dataset_1.expiry_date < timezone.now()

        self.uploads_dataset_1.publication_date = timezone.now()
        self.uploads_dataset_1.save()

        assert self.uploads_dataset_1.is_expired is False
        assert self.uploads_dataset_1.expiry_date is None

        self.uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        self.uploads_dataset_1.save()

        assert self.uploads_dataset_1.is_expired is False
        assert self.uploads_dataset_1.expiry_date is None
        assert UploadsDataset.objects.count() == 1

        remove_expired_dataset_drafts()
        assert UploadsDataset.objects.count() == 1

        self.uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        self.uploads_dataset_1.save()

        remove_expired_dataset_drafts()
        assert UploadsDataset.objects.count() == 1

        self.uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        self.uploads_dataset_1.publication_date = None
        self.uploads_dataset_1.save()

        remove_expired_dataset_drafts()
        assert UploadsDataset.objects.count() == 0

    def test_display_name(self):
        """
        Ensure the display name gets updated correctly.
        """
        assert self.uploads_dataset_1.display_name == self.uploads_dataset_1.name

        self.uploads_dataset_1.name = None
        self.uploads_dataset_1.save()
        assert self.uploads_dataset_1.display_name == str(self.uploads_dataset_1.pk)

        uploads_version_1 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
        )
        assert self.uploads_dataset_1.latest_version == uploads_version_1
        assert self.uploads_dataset_1.display_name == str(self.uploads_dataset_1.pk)

        uploads_version_1.name = "v1"
        uploads_version_1.save()
        assert self.uploads_dataset_1.display_name == str(self.uploads_dataset_1.pk)

        uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )
        uploads_version_2 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=uploads_version_file_1,
        )
        assert self.uploads_dataset_1.latest_version == uploads_version_2
        assert self.uploads_dataset_1.display_name == uploads_version_file_1.name

        metadata = set_metadata(
            assigned_to_content_type=uploads_version_file_1.get_content_type(),
            assigned_to_object_id=uploads_version_file_1.pk,
            custom_key="FILE_NAME",
            value=uploads_version_file_1.name,
            read_only=True,
        )
        assert self.uploads_dataset_1.display_name == metadata.get_value()

        metadata.set_value("random_file_name.jpg")
        self.uploads_dataset_1.refresh_from_db()
        assert self.uploads_dataset_1.display_name == "random_file_name.jpg"

        uploads_version_file_2 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )
        uploads_version_1.version_file = uploads_version_file_2
        uploads_version_1.save()
        self.uploads_dataset_1.refresh_from_db()
        assert self.uploads_dataset_1.display_name == "random_file_name.jpg"

        uploads_version_2.version_file = uploads_version_file_2
        uploads_version_2.save()
        self.uploads_dataset_1.refresh_from_db()
        assert self.uploads_dataset_1.display_name == uploads_version_file_2.name

        metadata.assigned_to_object_id = uploads_version_file_2.pk
        metadata.save()
        self.uploads_dataset_1.refresh_from_db()
        assert self.uploads_dataset_1.display_name == "random_file_name.jpg"

        metadata.delete()
        self.uploads_dataset_1.refresh_from_db()
        assert not Metadata.objects.filter(
            assigned_to_content_type=uploads_version_file_1.get_content_type(),
            assigned_to_object_id=uploads_version_file_1.pk,
            custom_key="FILE_NAME",
        ).exists()
        assert self.uploads_dataset_1.display_name == uploads_version_file_2.name

        uploads_version_file_3 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )
        uploads_version_3 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=uploads_version_file_3,
        )
        assert self.uploads_dataset_1.latest_version == uploads_version_3
        assert self.uploads_dataset_1.display_name == uploads_version_file_3.name

        self.uploads_dataset_1.name = "Dataset 1"
        self.uploads_dataset_1.save()
        self.uploads_dataset_1.refresh_from_db()
        assert self.uploads_dataset_1.display_name == "Dataset 1"

    def test_restore(self):
        """
        Ensure we can restore an uploads version.
        """
        assert self.uploads_dataset_1.uploads_versions.count() == 0

        uploads_version_file = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        uploads_version_1 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=uploads_version_file,
        )

        assert uploads_version_1.metadata.count() == 0
        assert self.uploads_dataset_1.uploads_versions.count() == 1
        assert self.uploads_dataset_1.latest_version == uploads_version_1

        with pytest.raises(PermissionDenied):
            self.uploads_dataset_1.restore_version(
                uploads_version=uploads_version_1,
            )

        uploads_version_2 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=uploads_version_file,
        )

        set_metadata(
            assigned_to_content_type=uploads_version_2.get_content_type(),
            assigned_to_object_id=uploads_version_2.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        assert uploads_version_2.metadata.count() == 1
        assert self.uploads_dataset_1.uploads_versions.count() == 2
        assert self.uploads_dataset_1.latest_version == uploads_version_2

        uploads_version_3 = self.uploads_dataset_1.restore_version(
            uploads_version=uploads_version_1,
        )

        assert uploads_version_3.metadata.count() == 0
        assert self.uploads_dataset_1.uploads_versions.count() == 3
        assert self.uploads_dataset_1.latest_version == uploads_version_3
        assert uploads_version_1 != uploads_version_3

        uploads_version_4 = self.uploads_dataset_1.restore_version(
            uploads_version=uploads_version_2,
        )

        assert uploads_version_4.metadata.count() == 1
        assert self.uploads_dataset_1.uploads_versions.count() == 4
        assert self.uploads_dataset_1.latest_version == uploads_version_4
        assert uploads_version_2 != uploads_version_4

        with pytest.raises(PermissionDenied):
            self.uploads_dataset_1.restore_version(
                uploads_version=uploads_version_4,
            )

        uploads_dataset_2 = UploadsDataset.objects.create(
            name="Dataset 2",
        )

        uploads_version_5 = UploadsVersion.objects.create(
            dataset=uploads_dataset_2,
        )

        with pytest.raises(PermissionDenied):
            self.uploads_dataset_1.restore_version(
                uploads_version=uploads_version_5,
            )

        assert self.uploads_dataset_1.uploads_versions.count() == 4
        assert self.uploads_dataset_1.latest_version == uploads_version_4


@pytest.mark.django_db
class TestUploadsDatasetLockMixin:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        project_1 = Project.objects.create(
            name="Project 1",
        )

        self.dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
            folder=project_1.folders.first(),
        )

    def test_lock(self, initial_users):
        """
        Ensure we have an expected lock behavior.
        """
        dataset = UploadsDataset.objects.get(pk=self.dataset_1.pk)
        dataset.name = "Dataset 1"
        dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None

        dataset.lock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None

        last_lock_time = dataset.locked_at

        dataset.lock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None
        assert dataset.locked_at > last_lock_time

        dataset.name = "Dataset 1 - Edit #1"
        dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #1"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None

        dataset.lock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #1"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None

        dataset.unlock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #1"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None

        dataset.lock()
        last_lock_time = dataset.locked_at

        dataset.name = "Dataset 1 - Edit #2"
        dataset.save(auto_unlock=False)

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #2"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None
        assert dataset.locked_at == last_lock_time

        last_lock_time = dataset.locked_at

        set_request_for_user(initial_users["user_2"])

        with pytest.raises(PermissionDenied):
            dataset.name = "Dataset 1 - Edit #3"
            dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #2"
        assert dataset.locked_at == last_lock_time

        dataset.name = "Dataset 1 - Edit #3"
        dataset.locked_at = timezone.now() - timezone.timedelta(minutes=settings.MAX_LOCK_TIME)
        dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #3"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None


@pytest.mark.django_db
class TestUploadsVersionModel:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        self.uploads_version_1 = UploadsVersion.objects.create()

    def test_string_representation(self):
        """
        Ensure we get the correct string representation of a version.
        """
        assert str(self.uploads_version_1) == f"{self.uploads_version_1.dataset}: {self.uploads_version_1.pk}"

    def test_string_representation_with_version_name(self):
        """
        Ensure we get the correct string representation of a version when its name is set.
        """
        self.uploads_version_1.name = "v1"
        self.uploads_version_1.save()

        assert str(self.uploads_version_1) == f"{self.uploads_version_1.dataset}: {self.uploads_version_1.name}"

    def test_get_all_metadata(self):
        """
        Ensure we get all the metadata of a version and its linked version file, folder and project.
        """
        project_1 = Project.objects.create(
            name="Project 1",
        )

        set_metadata(
            assigned_to_content_type=project_1.get_content_type(),
            assigned_to_object_id=project_1.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        assert len(project_1.metadata.all()) == 1

        set_metadata(
            assigned_to_content_type=project_1.folders.first().get_content_type(),
            assigned_to_object_id=project_1.folders.first().pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        assert len(project_1.folders.first().metadata.all()) == 1

        dataset_1 = UploadsDataset.objects.create(
            folder=project_1.folders.first(),
        )

        uploads_version_1 = UploadsVersion.objects.create(
            dataset=dataset_1,
        )

        set_metadata(
            assigned_to_content_type=uploads_version_1.get_content_type(),
            assigned_to_object_id=uploads_version_1.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        assert len(uploads_version_1.metadata.all()) == 1

        uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        set_metadata(
            assigned_to_content_type=uploads_version_file_1.get_content_type(),
            assigned_to_object_id=uploads_version_file_1.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        assert len(uploads_version_file_1.metadata.all()) == 1

        uploads_version_1.version_file = uploads_version_file_1
        uploads_version_1.save()

        assert len(uploads_version_1.get_all_metadata()) == 4

    def test_editing_already_published_versions(self):
        """
        Ensure we can't edit an already published version anymore which are not the latest version.
        """
        storage_1 = DynamicStorage.objects.get(
            default=True,
        )

        dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
        )

        project = Project.objects.create(
            name="Test project",
        )

        folder = project.folders.first()
        folder.storage = storage_1
        folder.save()

        uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        uploads_version_1 = UploadsVersion.objects.create(
            dataset=dataset_1,
        )
        uploads_version_1.version_file = uploads_version_file_1
        uploads_version_1.save()

        uploads_version_1.dataset.publish(folder=folder.pk)
        uploads_version_1.save()

        uploads_version_2 = UploadsVersion.objects.create(
            dataset=dataset_1,
        )
        uploads_version_2.version_file = uploads_version_file_1
        uploads_version_2.save()

        # TODO: Fix publishing by dataset and its related missing storage problem
        # uploads_version_2.publish(dataset=uploads_version_1.dataset.pk)
        # uploads_version_2.save()

        # with pytest.raises(PermissionDenied):
        #     uploads_version_1.save()

    def test_reset_status(self):
        """
        Ensure we can reset the status of a file.
        """
        assert self.uploads_version_1.status == UploadsVersion.Status.SCHEDULED

        self.uploads_version_1.status = UploadsVersion.Status.FINISHED
        self.uploads_version_1.save()
        assert self.uploads_version_1.status == UploadsVersion.Status.FINISHED

        self.uploads_version_1.reset_status()
        assert self.uploads_version_1.status == UploadsVersion.Status.SCHEDULED


@pytest.mark.django_db
class TestUploadsVersionLockMixin:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        project_1 = Project.objects.create(
            name="Project 1",
        )

        self.dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
            folder=project_1.folders.first(),
        )

        self.uploads_version_1 = UploadsVersion.objects.create(
            dataset=self.dataset_1,
        )

    def test_lock(self, initial_users):
        """
        Ensure we have an expected lock behavior.
        """
        dataset = UploadsDataset.objects.get(pk=self.dataset_1.pk)
        dataset.name = "Dataset 1"
        dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is False
        assert self.uploads_version_1.locked_by is None
        assert self.uploads_version_1.locked_at is None

        dataset.lock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is True
        assert self.uploads_version_1.locked_by == initial_users["user_1"]
        assert self.uploads_version_1.locked_at is not None

        last_lock_time = dataset.locked_at

        dataset.lock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None
        assert dataset.locked_at > last_lock_time

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is True
        assert self.uploads_version_1.locked_by == initial_users["user_1"]
        assert self.uploads_version_1.locked_at is not None
        assert self.uploads_version_1.locked_at > last_lock_time

        dataset.name = "Dataset 1 - Edit #1"
        dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #1"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is False
        assert self.uploads_version_1.locked_by is None
        assert self.uploads_version_1.locked_at is None

        dataset.lock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #1"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is True
        assert self.uploads_version_1.locked_by == initial_users["user_1"]
        assert self.uploads_version_1.locked_at is not None

        dataset.unlock()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #1"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is False
        assert self.uploads_version_1.locked_by is None
        assert self.uploads_version_1.locked_at is None

        dataset.lock()
        last_lock_time = dataset.locked_at

        dataset.name = "Dataset 1 - Edit #2"
        dataset.save(auto_unlock=False)

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #2"
        assert dataset.locked is True
        assert dataset.locked_by == initial_users["user_1"]
        assert dataset.locked_at is not None
        assert dataset.locked_at == last_lock_time

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is True
        assert self.uploads_version_1.locked_by == initial_users["user_1"]
        assert self.uploads_version_1.locked_at is not None
        assert self.uploads_version_1.locked_at == last_lock_time

        last_lock_time = dataset.locked_at

        set_request_for_user(initial_users["user_2"])

        with pytest.raises(PermissionDenied):
            dataset.name = "Dataset 1 - Edit #3"
            dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #2"
        assert dataset.locked_at == last_lock_time

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked_at == last_lock_time

        dataset.name = "Dataset 1 - Edit #3"
        dataset.locked_at = timezone.now() - timezone.timedelta(minutes=settings.MAX_LOCK_TIME)
        dataset.save()

        dataset.refresh_from_db()
        assert dataset.name == "Dataset 1 - Edit #3"
        assert dataset.locked is False
        assert dataset.locked_by is None
        assert dataset.locked_at is None

        self.uploads_version_1.refresh_from_db()
        assert self.uploads_version_1.locked is False
        assert self.uploads_version_1.locked_by is None
        assert self.uploads_version_1.locked_at is None


@pytest.mark.django_db
class TestUploadsVersionFileModel:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
            status=UploadsVersionFile.Status.FINISHED,
        )

    def test_reset_status(self):
        """
        Ensure we can reset the status of a file.
        """
        assert self.uploads_version_file_1.status == UploadsVersionFile.Status.FINISHED

        self.uploads_version_file_1.reset_status()
        assert self.uploads_version_file_1.status == UploadsVersionFile.Status.SCHEDULED


@pytest.mark.django_db
class TestUploadsVersionMetadataModel:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.uploads_version_1 = UploadsVersion.objects.create()

        self.uploads_version_metadata_1 = set_metadata(
            assigned_to_content_type=self.uploads_version_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_1.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        self.metadata_field_1 = MetadataField.objects.create(
            key="metadata_field_1",
            field_type=MetadataFieldType.TEXT,
            read_only=True,
        )

    def test_clean_method(self):
        """
        Ensure we get an error if we try to assign a custom key and a field at the same time, or none at all.
        """
        with pytest.raises(ValidationError):
            set_metadata(
                assigned_to_content_type=self.uploads_version_1.get_content_type(),
                assigned_to_object_id=self.uploads_version_1.pk,
                field=self.metadata_field_1,
                custom_key="custom_key_1",
                value="custom_value_1",
            )

        with pytest.raises(ValidationError):
            set_metadata(
                assigned_to_content_type=self.uploads_version_1.get_content_type(),
                assigned_to_object_id=self.uploads_version_1.pk,
                value="custom_value_1",
            )


@pytest.mark.django_db
class TestUploadsVersionFileMetadataModel:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        self.uploads_version_file_metadata_1 = set_metadata(
            assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_file_1.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        self.metadata_field_1 = MetadataField.objects.create(
            key="metadata_field_1",
            field_type=MetadataFieldType.TEXT,
            read_only=True,
        )

    def test_clean_method(self):
        """
        Ensure we get an error if we try to assign a custom key and a field at the same time, or none at all.
        """
        with pytest.raises(ValidationError):
            set_metadata(
                assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
                assigned_to_object_id=self.uploads_version_file_1.pk,
                field=self.metadata_field_1,
                custom_key="custom_key_1",
                value="custom_value_1",
            )

        with pytest.raises(ValidationError):
            set_metadata(
                assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
                assigned_to_object_id=self.uploads_version_file_1.pk,
                value="custom_value_1",
            )
