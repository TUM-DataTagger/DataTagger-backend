import datetime
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

import pytest
from conftest import auth_user

from fdm.core.helpers import get_content_type_for_object, set_request_for_user
from fdm.folders.models import Folder, FolderPermission
from fdm.metadata.enums import MetadataFieldType
from fdm.metadata.helpers import set_metadata
from fdm.metadata.models import Metadata, MetadataTemplate, MetadataTemplateField
from fdm.projects.models import Project, ProjectMembership
from fdm.storages.models import DynamicStorage
from fdm.uploads.models import UploadsDataset, UploadsVersion, UploadsVersionFile
from fdm.uploads.tasks import remove_expired_dataset_drafts

sample_file = SimpleUploadedFile(
    "file.jpg",
    b"",
    content_type="image/jpg",
)

sample_file2 = SimpleUploadedFile(
    "file2.jpg",
    b"",
    content_type="image/jpg",
)


@pytest.mark.django_db
class TestUploadsDatasetAPI:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        storage_1 = DynamicStorage.objects.get(
            default=True,
        )

        self.project_1 = Project.objects.create(
            name="Project 1",
        )

        self.folder_1 = self.project_1.folders.first()
        self.folder_1.storage = storage_1
        self.folder_1.save()

        self.folder_2 = Folder.objects.create(
            name="Folder 2",
            project=self.project_1,
        )

        self.folder_3 = Folder.objects.create(
            name="Folder 3",
            project=self.project_1,
        )

        self.uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
            folder=self.folder_1,
            publication_date=timezone.now(),
        )

        self.uploads_dataset_2 = UploadsDataset.objects.create(
            name="Dataset 2",
            folder=self.folder_1,
            publication_date=timezone.now(),
        )

        self.uploads_dataset_3 = UploadsDataset.objects.create(
            name="Dataset 3",
            folder=self.folder_2,
            publication_date=timezone.now(),
        )

        self.uploads_dataset_4 = UploadsDataset.objects.create(
            name="Dataset 4",
            folder=self.folder_3,
            publication_date=timezone.now(),
        )

        self.uploads_dataset_5 = UploadsDataset.objects.create(
            name="Dataset 5",
        )

    def test_read_uploads_dataset_list(self, client, initial_users):
        """
        Ensure we can read the uploads dataset list.
        """
        auth_user(client, initial_users["user_1"])

        url = reverse("uploads-dataset-list")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

        url_filter = f"{url}?folder={self.folder_1.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

        url_filter = f"{url}?folder={self.folder_1.pk}&search={self.uploads_dataset_1.name}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["pk"] == str(self.uploads_dataset_1.pk)

        url_filter = f"{url}?folder={self.folder_2.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

        url_filter = f"{url}?folder={self.folder_3.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_read_uploads_dataset_details(self, client):
        """
        Ensure we can read the uploads dataset details.
        """
        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_1.pk,
            },
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == self.uploads_dataset_1.name

    def test_change_uploads_dataset_details(self, client):
        """
        Ensure we can change the uploads dataset details.
        """
        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_1.pk,
            },
        )

        dataset_name = "Altered dataset name"

        response = client.patch(
            url,
            {
                "name": dataset_name,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == dataset_name

    def test_create_uploads_dataset(self, client):
        """
        Ensure we can create a new uploads dataset.
        """
        url = reverse("uploads-dataset-list")

        response = client.post(
            url,
            {
                "name": "Dataset 6",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Dataset 6"
        assert response.data["folder"] is None
        assert UploadsDataset.objects.all().count() == 6

        response = client.post(
            url,
            {
                "name": "Dataset 7",
                "folder": self.folder_1.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Dataset 7"
        assert response.data["folder"]["pk"] == str(self.folder_1.pk)
        assert UploadsDataset.objects.all().count() == 7

    def test_change_folder_protection(self, client):
        """
        Ensure we can't change the folder when updating an uploads dataset.
        """
        url = reverse("uploads-dataset-list")

        response = client.post(
            url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["folder"] is None

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": response.data["pk"],
            },
        )

        response = client.patch(
            url,
            {
                "folder": self.folder_1.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["folder"] is None

        url = reverse("uploads-dataset-list")

        response = client.post(
            url,
            {
                "folder": self.folder_1.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["folder"]["pk"] == str(self.folder_1.pk)

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": response.data["pk"],
            },
        )

        response = client.patch(
            url,
            {
                "folder": self.folder_2.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["folder"]["pk"] == str(self.folder_1.pk)

        response = client.patch(
            url,
            {
                "folder": None,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["folder"]["pk"] == str(self.folder_1.pk)

    def test_read_uploads_dataset_list_with_folder_permission(self, client, initial_users):
        """
        Ensure we can read the uploads dataset list.
        """
        auth_user(client, initial_users["user_2"])

        url = reverse("uploads-dataset-list")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

        url_filter = f"{url}?folder={self.folder_1.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

        url_filter = f"{url}?folder={self.folder_2.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

        url_filter = f"{url}?folder={self.folder_3.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

        membership = ProjectMembership.objects.create(
            project=self.project_1,
            member=initial_users["user_2"],
        )

        FolderPermission.objects.create(
            folder=self.folder_2,
            project_membership=membership,
        )

        FolderPermission.objects.create(
            folder=self.folder_3,
            project_membership=membership,
        )

        url_filter = f"{url}?folder={self.folder_1.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

        url_filter = f"{url}?folder={self.folder_2.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

        url_filter = f"{url}?folder={self.folder_3.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_uploads_dataset_file_action(self, client):
        """
        Ensure we can upload a file for an uploads dataset.
        """
        dataset = UploadsDataset.objects.create()

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": dataset.pk,
            },
        )

        # We can't use reverse for the action as this would collide with other routers
        file_action_url = f"{url}file/"
        version_action_url = f"{url}version/"

        assert dataset.publication_date is None
        assert dataset.is_published() is False
        assert dataset.uploads_versions.count() == 0
        assert dataset.latest_version is None

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert (
            UploadsVersionFile.objects.get(pk=response.data["version_file"]["pk"])
            .metadata.filter(custom_key="MIME_TYPE")
            .exists()
        )

        assert dataset.publication_date is None
        assert dataset.is_published() is False
        assert dataset.uploads_versions.count() == 1
        assert dataset.latest_version is not None
        assert str(dataset.latest_version.pk) == response.data["pk"]
        assert dataset.latest_version.publication_date is None
        assert dataset.latest_version.is_published() is False

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": response.data["pk"],
            },
        )

        response = client.patch(
            url,
            {
                "name": "v1",
                "metadata": [
                    {
                        "custom_key": "custom_key_1",
                        "value": "custom value 1",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        assert dataset.publication_date is None
        assert dataset.is_published() is False
        assert dataset.latest_version is not None
        assert dataset.latest_version.name == "v1"
        assert dataset.latest_version.metadata.count() == 0
        assert dataset.latest_version.publication_date is None
        assert dataset.latest_version.is_published() is False

        response = client.post(
            version_action_url,
            {
                "metadata": [
                    {
                        "custom_key": "custom_key_1",
                        "value": "custom value 1",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset.publication_date is None
        assert dataset.is_published() is False
        assert dataset.latest_version is not None
        assert dataset.latest_version.name is None
        assert dataset.latest_version.metadata.count() == 1
        assert dataset.latest_version.metadata.first().custom_key == "custom_key_1"
        assert dataset.latest_version.metadata.first().get_value() == "custom value 1"
        assert dataset.latest_version.publication_date is None
        assert dataset.latest_version.is_published() is False

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset.publication_date is None
        assert dataset.is_published() is False
        assert dataset.uploads_versions.count() == 3
        assert dataset.latest_version is not None
        assert str(dataset.latest_version.pk) == response.data["pk"]
        assert dataset.latest_version.name is None
        assert dataset.latest_version.metadata.count() == 1
        assert dataset.latest_version.metadata.first().custom_key == "custom_key_1"
        assert dataset.latest_version.metadata.first().get_value() == "custom value 1"
        assert dataset.latest_version.publication_date is None
        assert dataset.latest_version.is_published() is False

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": response.data["pk"],
            },
        )

        response = client.patch(
            url,
            {
                "name": "v2",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        assert dataset.publication_date is None
        assert dataset.is_published() is False
        assert dataset.latest_version is not None
        assert dataset.latest_version.name == "v2"
        assert dataset.latest_version.metadata.count() == 1
        assert dataset.latest_version.metadata.first().custom_key == "custom_key_1"
        assert dataset.latest_version.metadata.first().get_value() == "custom value 1"
        assert dataset.latest_version.publication_date is None
        assert dataset.latest_version.is_published() is False

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset.publication_date is None
        assert dataset.is_published() is False
        assert dataset.uploads_versions.count() == 4
        assert dataset.latest_version is not None
        assert str(dataset.latest_version.pk) == response.data["pk"]
        assert dataset.latest_version.name is None
        assert dataset.latest_version.metadata.count() == 1
        assert dataset.latest_version.metadata.first().custom_key == "custom_key_1"
        assert dataset.latest_version.metadata.first().get_value() == "custom value 1"
        assert dataset.latest_version.publication_date is None
        assert dataset.latest_version.is_published() is False

        dataset.publish(folder=self.folder_1.pk)

        assert dataset.publication_date is not None
        assert dataset.is_published() is True
        assert all([uploads_version.publication_date is not None for uploads_version in dataset.uploads_versions.all()])
        assert all([uploads_version.is_published() for uploads_version in dataset.uploads_versions.all()])

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset.publication_date is not None
        assert dataset.is_published() is True
        assert dataset.uploads_versions.count() == 5
        assert dataset.latest_version is not None
        assert str(dataset.latest_version.pk) == response.data["pk"]
        assert dataset.latest_version.name is None
        assert dataset.latest_version.metadata.count() == 1
        assert dataset.latest_version.metadata.first().custom_key == "custom_key_1"
        assert dataset.latest_version.metadata.first().get_value() == "custom value 1"
        assert dataset.latest_version.publication_date is not None
        assert dataset.latest_version.is_published() is True

    def test_uploads_dataset_file_upload_with_metadata_from_templates(self, client, initial_users):
        """
        Ensure we can upload a file for an uploads dataset, and they automatically receive metadata from templates.
        """
        set_request_for_user(initial_users["user_1"])

        dataset_1 = UploadsDataset.objects.create()

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": dataset_1.pk,
            },
        )

        # We can't use reverse for the action as this would collide with other routers
        file_action_url = f"{url}file/"

        assert dataset_1.uploads_versions.count() == 0
        assert dataset_1.latest_version is None

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_1.uploads_versions.count() == 1
        assert dataset_1.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_1.latest_version.get_content_type(),
            ).count()
            == 0
        )
        assert dataset_1.latest_version.metadata.count() == 0
        assert str(dataset_1.latest_version.pk) == response.data["pk"]

        set_request_for_user(initial_users["user_1"])

        project_1 = Project.objects.create(
            name="Project 1",
        )
        assert project_1.metadata_template is None

        folder_1 = project_1.folders.first()
        assert folder_1.metadata_template is None

        dataset_2 = UploadsDataset.objects.create()

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": dataset_2.pk,
            },
        )

        # We can't use reverse for the action as this would collide with other routers
        file_action_url = f"{url}file/"
        publish_action_url = f"{url}publish/"

        assert dataset_2.uploads_versions.count() == 0
        assert dataset_2.latest_version is None

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_2.uploads_versions.count() == 1
        assert dataset_2.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_2.latest_version.get_content_type(),
            ).count()
            == 0
        )
        assert dataset_2.latest_version.metadata.count() == 0

        response = client.post(
            publish_action_url,
            {
                "folder": folder_1.pk,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_2.uploads_versions.count() == 1
        assert dataset_2.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_2.latest_version.get_content_type(),
            ).count()
            == 0
        )
        assert dataset_2.latest_version.metadata.count() == 0
        assert str(dataset_2.latest_version.pk) == response.data["latest_version"]["pk"]

        set_request_for_user(initial_users["user_1"])

        metadata_template_1 = MetadataTemplate.objects.create(
            name="Metadata template 1",
        )

        metadata_template_field_1 = MetadataTemplateField.objects.create(
            metadata_template=metadata_template_1,
            custom_key="integer_1",
            field_type=MetadataFieldType.INTEGER,
        )
        metadata_template_field_1.set_value("1337")

        folder_1.metadata_template = metadata_template_1
        folder_1.save()

        dataset_3 = UploadsDataset.objects.create()

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": dataset_3.pk,
            },
        )

        # We can't use reverse for the action as this would collide with other routers
        file_action_url = f"{url}file/"
        publish_action_url = f"{url}publish/"

        assert dataset_3.uploads_versions.count() == 0
        assert dataset_3.latest_version is None

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_3.uploads_versions.count() == 1
        assert dataset_3.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_3.latest_version.get_content_type(),
            ).count()
            == 0
        )
        assert dataset_3.latest_version.metadata.count() == 0

        response = client.post(
            publish_action_url,
            {
                "folder": folder_1.pk,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_3.uploads_versions.count() == 2
        assert dataset_3.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_3.latest_version.get_content_type(),
            ).count()
            == 1
        )
        assert dataset_3.latest_version.metadata.count() == 1
        integer_1 = dataset_3.latest_version.metadata.filter(custom_key="integer_1")
        assert integer_1.exists()
        assert integer_1.first().get_value() == "1337"
        assert integer_1.first().metadata_template_field == metadata_template_field_1
        assert str(dataset_3.latest_version.pk) == response.data["latest_version"]["pk"]

        set_request_for_user(initial_users["user_1"])

        metadata_template_2 = MetadataTemplate.objects.create(
            name="Metadata template 2",
        )

        metadata_template_field_2 = MetadataTemplateField.objects.create(
            metadata_template=metadata_template_2,
            custom_key="text_1",
            field_type=MetadataFieldType.TEXT,
        )
        metadata_template_field_2.set_value("Text")

        project_1.metadata_template = metadata_template_2
        project_1.save()

        dataset_4 = UploadsDataset.objects.create()

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": dataset_4.pk,
            },
        )

        # We can't use reverse for the action as this would collide with other routers
        file_action_url = f"{url}file/"
        publish_action_url = f"{url}publish/"

        assert dataset_4.uploads_versions.count() == 0
        assert dataset_4.latest_version is None

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_4.uploads_versions.count() == 1
        assert dataset_4.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_4.latest_version.get_content_type(),
            ).count()
            == 1
        )
        assert dataset_4.latest_version.metadata.count() == 0

        response = client.post(
            publish_action_url,
            {
                "folder": folder_1.pk,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_4.uploads_versions.count() == 2
        assert dataset_4.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_4.latest_version.get_content_type(),
            ).count()
            == 3
        )
        assert dataset_4.latest_version.metadata.count() == 2
        integer_1 = dataset_4.latest_version.metadata.filter(custom_key="integer_1")
        assert integer_1.exists()
        assert integer_1.first().get_value() == "1337"
        assert integer_1.first().metadata_template_field == metadata_template_field_1
        text_1 = dataset_4.latest_version.metadata.filter(custom_key="text_1")
        assert text_1.exists()
        assert text_1.first().get_value() == "Text"
        assert text_1.first().metadata_template_field == metadata_template_field_2
        assert str(dataset_4.latest_version.pk) == response.data["latest_version"]["pk"]

        set_request_for_user(initial_users["user_1"])

        metadata_template_field_2.set_value("Altered text")

        metadata_template_field_3 = MetadataTemplateField.objects.create(
            metadata_template=metadata_template_2,
            custom_key="text_2",
            field_type=MetadataFieldType.TEXT,
        )
        metadata_template_field_3.set_value("Text 2")

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        assert dataset_4.uploads_versions.count() == 3
        assert dataset_4.latest_version is not None
        assert (
            Metadata.objects.filter(
                assigned_to_content_type=dataset_4.latest_version.get_content_type(),
            ).count()
            == 5
        )
        assert dataset_4.latest_version.metadata.count() == 2
        integer_1 = dataset_4.latest_version.metadata.filter(custom_key="integer_1")
        assert integer_1.exists()
        assert integer_1.first().get_value() == "1337"
        assert integer_1.first().metadata_template_field == metadata_template_field_1
        text_1 = dataset_4.latest_version.metadata.filter(custom_key="text_1")
        assert text_1.exists()
        assert text_1.first().get_value() == "Text"
        assert text_1.first().metadata_template_field == metadata_template_field_2
        assert str(dataset_4.latest_version.pk) == response.data["pk"]

    def test_uploads_dataset_restore_action(self, client, initial_users):
        """
        Ensure we can restore an uploads version by making a POST request to the respective dataset action endpoint.
        """
        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_1.pk,
            },
        )
        version_action_url = f"{url}version/"
        file_action_url = f"{url}file/"
        restore_action_url = f"{url}restore/"

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 0

        response = client.post(
            file_action_url,
            {
                "file": sample_file,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

        uploads_version_1_url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": response.data["pk"],
            },
        )

        response = client.patch(
            uploads_version_1_url,
            {
                "name": "v1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        uploads_version_1 = response.data
        assert uploads_version_1["name"] == "v1"
        assert len(uploads_version_1["metadata"]) == 0

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 1
        assert response.data["uploads_versions"][0]["pk"] == uploads_version_1["pk"]

        response = client.post(
            restore_action_url,
            {
                "uploads_version": uploads_version_1["pk"],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = client.post(
            version_action_url,
            {
                "metadata": [
                    {
                        "custom_key": "custom_key_1",
                        "field_type": MetadataFieldType.TEXT,
                        "value": "custom value 1",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        uploads_version_2 = response.data
        assert uploads_version_2["name"] is None
        assert len(uploads_version_2["metadata"]) == 1

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 2
        assert response.data["uploads_versions"][0]["pk"] == uploads_version_2["pk"]

        response = client.post(
            restore_action_url,
            {
                "uploads_version": uploads_version_1["pk"],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        uploads_version_3 = response.data
        assert uploads_version_3["name"] is None
        assert len(uploads_version_3["metadata"]) == 0

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 3
        assert uploads_version_1["pk"] != uploads_version_3["pk"]
        assert response.data["uploads_versions"][0]["pk"] == uploads_version_3["pk"]

        response = client.post(
            restore_action_url,
            {
                "uploads_version": uploads_version_2["pk"],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        uploads_version_4 = response.data
        assert uploads_version_4["name"] is None
        assert len(uploads_version_4["metadata"]) == 1

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 4
        assert uploads_version_2["pk"] != uploads_version_4["pk"]
        assert response.data["uploads_versions"][0]["pk"] == uploads_version_4["pk"]

        response = client.post(
            restore_action_url,
            {
                "uploads_version": uploads_version_4["pk"],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        uploads_dataset_2 = UploadsDataset.objects.create(
            name="Dataset 2",
            folder=self.folder_1,
            publication_date=timezone.now(),
        )

        uploads_version_5 = UploadsVersion.objects.create(
            dataset=uploads_dataset_2,
            publication_date=timezone.now(),
        )

        response = client.post(
            restore_action_url,
            {
                "uploads_version": uploads_version_5.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_uploads_dataset_version_action(self, client, initial_users):
        """
        Ensure we can create a new uploads version by making a POST request to the respective dataset action endpoint.
        """
        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_1.pk,
            },
        )
        action_url = f"{url}version/"

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 0

        response = client.post(action_url, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=uploads_version_file_1,
            publication_date=timezone.now(),
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 1

        response = client.post(
            action_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] is None
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED
        assert response.data["version_file"]["pk"] == str(uploads_version_file_1.pk)
        assert len(response.data["metadata"]) == 0

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 2

        response = client.post(
            action_url,
            {
                "name": "Specific version name",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Specific version name"
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED
        assert response.data["version_file"]["pk"] == str(uploads_version_file_1.pk)
        assert len(response.data["metadata"]) == 0

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 3

        response = client.post(
            action_url,
            {
                "name": "Another specific version name",
                "metadata": [
                    {
                        "custom_key": "custom_key_1",
                        "value": "custom value 1",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Another specific version name"
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED
        assert response.data["version_file"]["pk"] == str(uploads_version_file_1.pk)
        assert len(response.data["metadata"]) == 1

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 4

        response = client.post(
            action_url,
            {
                "name": "Named version 3",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Named version 3"
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED
        assert response.data["version_file"]["pk"] == str(uploads_version_file_1.pk)
        assert len(response.data["metadata"]) == 0

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 5

        response = client.post(
            action_url,
            {
                "name": "v4",
                "metadata": [
                    {
                        "custom_key": "custom_key_1",
                        "value": "custom value 1",
                    },
                    {
                        "custom_key": "custom_key_2",
                        "value": "custom value 2",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "v4"
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED
        assert response.data["version_file"]["pk"] == str(uploads_version_file_1.pk)
        assert len(response.data["metadata"]) == 2

        uploads_version_file_2 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        uploads_version = UploadsVersion.objects.get(pk=response.data["pk"])
        uploads_version.version_file = uploads_version_file_2
        uploads_version.save()

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 6

        response = client.post(
            action_url,
            {
                "name": "v5",
                "metadata": [],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "v5"
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED
        assert response.data["version_file"]["pk"] == str(uploads_version_file_2.pk)
        assert len(response.data["metadata"]) == 0

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["uploads_versions"]) == 7

        auth_user(client, initial_users["user_2"])

        response = client.post(
            action_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_read_uploads_dataset_details_with_folder_permission(self, client, initial_users):
        """
        Ensure we can read the uploads dataset details with folder permissions.
        """
        auth_user(client, initial_users["user_2"])

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_1.pk,
            },
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_2.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_3.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_4.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        membership = ProjectMembership.objects.create(
            project=self.project_1,
            member=initial_users["user_2"],
        )

        FolderPermission.objects.create(
            folder=self.folder_1,
            project_membership=membership,
        )

        FolderPermission.objects.create(
            folder=self.folder_2,
            project_membership=membership,
        )

        FolderPermission.objects.create(
            folder=self.folder_3,
            project_membership=membership,
        )

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_2.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == self.uploads_dataset_2.name

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_3.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == self.uploads_dataset_3.name

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_4.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == self.uploads_dataset_4.name

    def test_delete(self, client, initial_users):
        """
        Ensure we can delete a dataset as long as it has not been published or locked.
        """
        set_request_for_user(initial_users["user_1"])

        uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
        )
        uploads_dataset_1_pk = uploads_dataset_1.pk

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

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": uploads_dataset_1.pk,
            },
        )

        auth_user(client, initial_users["user_2"])

        response = client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()

        auth_user(client, initial_users["user_1"])

        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": uploads_dataset_2.pk,
            },
        )
        lock_url = f"{url}lock/"

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert not UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert not UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert not os.path.exists(version_file_path)

    def test_delete_protection(self, client, initial_users):
        """
        Ensure we can't delete a dataset if it has been published or locked.
        """
        set_request_for_user(initial_users["user_1"])

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_1.pk,
            },
        )

        response = client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert UploadsDataset.objects.filter(pk=self.uploads_dataset_1.pk).exists()

        version_file = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        uploads_version = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_2,
            version_file=version_file,
        )

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_2.pk,
            },
        )

        response = client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert UploadsDataset.objects.filter(pk=self.uploads_dataset_2.pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version.pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": uploads_version.pk,
            },
        )

        response = client.delete(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert UploadsDataset.objects.filter(pk=self.uploads_dataset_2.pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version.pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

        set_request_for_user(initial_users["user_1"])

        self.uploads_dataset_2.publication_date = None
        self.uploads_dataset_2.save()
        assert self.uploads_dataset_2.publication_date is None
        assert self.uploads_dataset_2.is_published() is False

        self.uploads_dataset_2.lock()
        assert self.uploads_dataset_2.locked is True
        assert self.uploads_dataset_2.locked_by == initial_users["user_1"]
        assert self.uploads_dataset_2.locked_at is not None

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_dataset_2.pk,
            },
        )

        response = client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert UploadsDataset.objects.filter(pk=self.uploads_dataset_2.pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version.pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": uploads_version.pk,
            },
        )

        response = client.delete(url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert UploadsDataset.objects.filter(pk=self.uploads_dataset_2.pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version.pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file.pk).exists()

    def test_bulk_delete(self, client, initial_users):
        """
        Ensure we can bulk delete datasets as long as none have been published.
        """
        set_request_for_user(initial_users["user_1"])

        uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
        )
        uploads_dataset_1_pk = uploads_dataset_1.pk

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

        set_request_for_user(initial_users["user_2"])

        uploads_dataset_3 = UploadsDataset.objects.create(
            name="Dataset 3",
        )
        uploads_dataset_3_pk = uploads_dataset_3.pk

        set_request_for_user(initial_users["user_1"])

        url = reverse("uploads-dataset-list")
        action_url = f"{url}bulk-delete/"

        auth_user(client, initial_users["user_2"])

        response = client.post(
            action_url,
            {
                "uploads_datasets": [
                    uploads_dataset_1.pk,
                    uploads_dataset_2.pk,
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_3_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert os.path.exists(version_file_path)

        auth_user(client, initial_users["user_1"])

        response = client.post(
            action_url,
            {
                "uploads_datasets": [
                    "7a49c23c-fa4d-4cb2-a619-abc4c2b3bbb1",
                    uploads_dataset_1.pk,
                    uploads_dataset_2.pk,
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_3_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert os.path.exists(version_file_path)

        response = client.post(
            action_url,
            {
                "uploads_datasets": [],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_3_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert os.path.exists(version_file_path)

        response = client.post(
            action_url,
            {
                "uploads_datasets": [
                    uploads_dataset_1.pk,
                    uploads_dataset_2.pk,
                    uploads_dataset_3.pk,
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_3_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert os.path.exists(version_file_path)

        uploads_dataset_2.publication_date = timezone.now()
        uploads_dataset_2.save()

        response = client.post(
            action_url,
            {
                "uploads_datasets": [
                    uploads_dataset_1.pk,
                    uploads_dataset_2.pk,
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_3_pk).exists()
        assert UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert os.path.exists(version_file_path)

        uploads_dataset_2.publication_date = None
        uploads_dataset_2.save()

        response = client.post(
            action_url,
            {
                "uploads_datasets": [
                    uploads_dataset_1.pk,
                    uploads_dataset_2.pk,
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["success"]) == 2
        assert str(uploads_dataset_1_pk) in response.data["success"]
        assert str(uploads_dataset_2_pk) in response.data["success"]
        assert len(response.data["error"]) == 0
        assert not UploadsDataset.objects.filter(pk=uploads_dataset_1_pk).exists()
        assert not UploadsDataset.objects.filter(pk=uploads_dataset_2_pk).exists()
        assert UploadsDataset.objects.filter(pk=uploads_dataset_3_pk).exists()
        assert not UploadsVersion.objects.filter(pk=uploads_version_pk).exists()
        assert not UploadsVersionFile.objects.filter(pk=version_file_pk).exists()
        assert not os.path.exists(version_file_path)

    def test_check_expired_draft(self, client, initial_users):
        """
        Ensure we can determine if a dataset in the drafts section has expired.
        """
        set_request_for_user(initial_users["user_1"])

        folder = Folder.objects.create(
            name="Folder",
            project=self.project_1,
        )

        uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
        )

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": uploads_dataset_1.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_expired"] is False
        assert response.data["expiry_date"] is not None
        assert datetime.datetime.fromisoformat(response.data["expiry_date"]) > timezone.now()

        uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        uploads_dataset_1.save()

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_expired"] is True
        assert response.data["expiry_date"] is not None
        assert datetime.datetime.fromisoformat(response.data["expiry_date"]) < timezone.now()

        uploads_dataset_1.publication_date = timezone.now()
        uploads_dataset_1.folder = folder
        uploads_dataset_1.save()

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_expired"] is False
        assert response.data["expiry_date"] is None

        uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        uploads_dataset_1.save()

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_expired"] is False
        assert response.data["expiry_date"] is None

        url = reverse("uploads-dataset-list")
        url_filter = f"{url}?folder={folder.pk}"

        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

        remove_expired_dataset_drafts()
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

        uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        uploads_dataset_1.save()

        remove_expired_dataset_drafts()
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

        uploads_dataset_1.creation_date = timezone.now() - timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)
        uploads_dataset_1.publication_date = None
        uploads_dataset_1.folder = None
        uploads_dataset_1.save()

        remove_expired_dataset_drafts()
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_bulk_publish_datasets(self, client, initial_users):
        """
        Ensure we can publish uploads datasets in bulk.
        """
        set_request_for_user(initial_users["user_1"])

        uploads_dataset_1 = UploadsDataset.objects.create()
        uploads_dataset_2 = UploadsDataset.objects.create()
        uploads_dataset_3 = UploadsDataset.objects.create()

        url = reverse("uploads-dataset-bulk-publish")

        # This request must trigger: "You must provide at least one uploads dataset."
        response = client.post(
            url,
            {
                "folder": self.folder_1.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # This request must trigger: "At least one uploads dataset provided does not exist."
        response = client.post(
            url,
            {
                "uploads_datasets": [
                    "7a49c23c-fa4d-4cb2-a619-abc4c2b3bbb1",
                ],
                "folder": self.folder_1.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # This request must trigger: "A folder with this primary key does not exist."
        response = client.post(
            url,
            {
                "uploads_datasets": [
                    uploads_dataset_1.pk,
                ],
                "folder": "7a49c23c-fa4d-4cb2-a619-abc4c2b3bbb1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        assert uploads_dataset_1.publication_date is None
        assert uploads_dataset_1.is_published() is False

        assert uploads_dataset_2.publication_date is None
        assert uploads_dataset_2.is_published() is False

        assert uploads_dataset_3.publication_date is None
        assert uploads_dataset_3.is_published() is False

        response = client.post(
            url,
            {
                "uploads_datasets": [
                    uploads_dataset_1.pk,
                    uploads_dataset_2.pk,
                    uploads_dataset_3.pk,
                ],
                "folder": self.folder_1.pk,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        uploads_dataset_1.refresh_from_db()
        assert uploads_dataset_1.publication_date is not None
        assert uploads_dataset_1.is_published() is True

        uploads_dataset_2.refresh_from_db()
        assert uploads_dataset_2.publication_date is not None
        assert uploads_dataset_2.is_published() is True

        uploads_dataset_3.refresh_from_db()
        assert uploads_dataset_3.publication_date is not None
        assert uploads_dataset_3.is_published() is True


@pytest.mark.django_db
class TestUploadsDatasetLockStatusMixin:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        self.project_1 = Project.objects.create(
            name="Project 1",
        )

        self.dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
            folder=self.project_1.folders.first(),
        )

    def test_lock(self, client, initial_users):
        """
        Ensure we have an expected lock behavior.
        """
        set_request_for_user(initial_users["user_1"])

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.dataset_1.pk,
            },
        )

        lock_url = f"{url}lock/"
        unlock_url = f"{url}unlock/"
        status_url = f"{url}status/"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.patch(
            url,
            {
                "name": "Dataset 1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dataset 1"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        last_lock_time = response.data["locked_at"]

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None
        assert response.data["locked_at"] > last_lock_time

        response = client.patch(
            url,
            {
                "name": "Dataset 1 - Edit #1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dataset 1 - Edit #1"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        auth_user(client, initial_users["user_2"])

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        assert self.project_1.members_count == 1
        assert self.project_1.folders.first().members_count == 1

        ProjectMembership.objects.create(
            project=self.project_1,
            member=initial_users["user_2"],
            is_project_admin=True,
        )

        assert self.project_1.members_count == 2
        assert self.project_1.folders.first().members_count == 2

        folder_permission = FolderPermission.objects.get(
            project_membership__member=initial_users["user_2"],
            folder=self.project_1.folders.first(),
        )
        assert folder_permission.is_folder_admin is True
        assert folder_permission.is_metadata_template_admin is True
        assert folder_permission.can_edit is True

        response = client.patch(
            url,
            {
                "name": "Dataset 1 - Edit #3",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dataset 1 - Edit #3"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_2"].pk
        assert response.data["locked_at"] is not None

        auth_user(client, initial_users["user_1"])

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        auth_user(client, initial_users["user_2"])

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        auth_user(client, initial_users["user_1"])

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None


@pytest.mark.django_db
class TestUploadsVersionAPI:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        storage_1 = DynamicStorage.objects.get(
            default=True,
        )

        self.project_1 = Project.objects.create(
            name="Project 1",
        )

        self.folder_1 = self.project_1.folders.first()
        self.folder_1.storage = storage_1
        self.folder_1.save()

        self.uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
        )

        self.uploads_version_1 = UploadsVersion.objects.create(
            dataset=uploads_dataset_1,
            version_file=self.uploads_version_file_1,
        )

    def test_read_uploads_version_list(self, client):
        """
        Ensure we can't read the uploads versions list without any filter.
        """
        url = reverse("uploads-version-list")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_create_uploads_version(self, client):
        """
        Ensure we can't create a new uploads version on its own.
        """
        url = reverse("uploads-version-list")

        response = client.post(url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_read_uploads_version_details(self, client):
        """
        Ensure we can read the uploads version details.
        """
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["pk"] == str(self.uploads_version_1.pk)

    def test_check_uploads_version_status(self, client):
        """
        Ensure the status of the uploads version changes after an update.
        """
        self.uploads_version_1.status = UploadsVersion.Status.SCHEDULED
        self.uploads_version_1.save()

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED

        self.uploads_version_1.status = UploadsVersion.Status.FINISHED
        self.uploads_version_1.save()

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == UploadsVersion.Status.FINISHED

        response = client.patch(
            url,
            {
                "metadata": [
                    {
                        "custom_key": "custom_key_1",
                        "value": "custom value 1",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["metadata"]) == 0
        assert response.data["status"] == UploadsVersion.Status.FINISHED

        response = client.patch(
            url,
            {
                "status": UploadsVersion.Status.SCHEDULED,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED

    def test_change_uploads_version_details(self, client):
        """
        Ensure we can change the uploads version details.
        """
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == self.uploads_version_1.name
        assert response.data["status"] == UploadsVersion.Status.SCHEDULED

        name = "Test name"

        response = client.patch(
            url,
            {
                "name": name,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == name

        response = client.patch(
            url,
            {
                "metadata": [
                    {
                        "custom_key": "custom_key_1",
                        "value": "custom value 1",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["metadata"]) == 0

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.uploads_version_1.dataset.pk,
            },
        )

        # We can't use reverse for the action as this would collide with other routers
        action_url = f"{url}publish/"

        response = client.post(
            action_url,
            {
                "folder": self.project_1.folders.first().pk,
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["publication_date"] is not None

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )

        name = "Test name 2"

        response = client.patch(
            url,
            {
                "name": name,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == name

    def test_filter_versions_by_dataset_folder_excludes_versions_without_dataset(self, client):
        """
        Test that filtering versions by dataset__folder no longer returns versions without a dataset.
        This test verifies the fix that removed outdated functionality that allowed listing
        versions without a dataset when filtering by dataset__folder.
        """
        # Create a version without a dataset (previously could be returned incorrectly)
        uploads_version_without_dataset = UploadsVersion.objects.create(
            name="Version without dataset",
            publication_date=timezone.now(),  # Make it published
        )

        # Create a dataset in folder_1 and a version with this dataset
        dataset_with_folder = UploadsDataset.objects.create(
            name="Dataset with folder",
            folder=self.folder_1,
            publication_date=timezone.now(),  # Make it published
        )
        uploads_version_with_dataset = UploadsVersion.objects.create(
            name="Version with dataset",
            dataset=dataset_with_folder,
            publication_date=timezone.now(),  # Make it published
        )

        # Test filtering by dataset__folder - should only return versions with datasets
        url = reverse("uploads-version-list")
        response = client.get(f"{url}?dataset__folder={self.folder_1.pk}", format="json")

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # Verify that only versions with datasets are returned
        version_ids = [item["pk"] for item in results]
        assert str(uploads_version_with_dataset.pk) in version_ids
        assert str(uploads_version_without_dataset.pk) not in version_ids

    def test_filter_versions_by_dataset_with_permissions(self, client, initial_users):
        """
        Test that filtering versions by dataset respects folder permissions.
        """
        # A user without permissions
        user_2 = initial_users["user_2"]

        # Create two datasets in different folders
        folder_2 = Folder.objects.create(
            name="Folder 2",
            project=self.project_1,
            storage=self.folder_1.storage,
        )

        # Dataset in folder_1 (accessible to user_1)
        dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
            folder=self.folder_1,
            publication_date=timezone.now(),
        )
        version_1 = UploadsVersion.objects.create(
            name="Version 1",
            dataset=dataset_1,
            publication_date=timezone.now(),
        )

        # Dataset in folder_2 (we'll grant permission to user_2)
        dataset_2 = UploadsDataset.objects.create(
            name="Dataset 2",
            folder=folder_2,
            publication_date=timezone.now(),
        )
        version_2 = UploadsVersion.objects.create(
            name="Version 2",
            dataset=dataset_2,
            publication_date=timezone.now(),
        )

        assert self.folder_1.members_count == 1

        assert folder_2.members_count == 1

        # Give user_2 permission to folder_2 but not folder_1
        project_membership_2 = ProjectMembership.objects.create(
            project=self.project_1,
            member=initial_users["user_2"],
        )

        FolderPermission.objects.create(
            folder=folder_2,
            project_membership=project_membership_2,
        )

        assert folder_2.members_count == 2

        # Test filtering by dataset with user_1
        url = reverse("uploads-version-list")
        response = client.get(f"{url}?dataset={dataset_1.pk}", format="json")
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["pk"] == str(version_1.pk)

        response = client.get(f"{url}?dataset={dataset_2.pk}", format="json")
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["pk"] == str(version_2.pk)

        # Switch to user_2
        set_request_for_user(user_2)
        client.force_authenticate(user=user_2)

        # user_2 can't access dataset_1's versions
        response = client.get(f"{url}?dataset={dataset_1.pk}", format="json")
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 0  # No results due to permission check

        # But user_2 can access dataset_2's versions
        response = client.get(f"{url}?dataset={dataset_2.pk}", format="json")
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["pk"] == str(version_2.pk)

    def test_folder_viewable_queryset_excludes_versions_without_dataset(self):
        """
        Test that the folder_viewable queryset method properly excludes versions without datasets
        when filtering by dataset__folder. This verifies the fix for the outdated functionality.
        """
        # Create a version without a dataset
        version_without_dataset = UploadsVersion.objects.create(
            name="Version without dataset",
            publication_date=timezone.now(),  # Make it published
        )

        # Create a version with a dataset in folder_1
        dataset_in_folder = UploadsDataset.objects.create(
            name="Dataset in folder",
            folder=self.folder_1,
            publication_date=timezone.now(),  # Make it published
        )
        version_with_dataset = UploadsVersion.objects.create(
            name="Version with dataset",
            dataset=dataset_in_folder,
            publication_date=timezone.now(),  # Make it published
        )

        # Get versions using the folder_viewable queryset method
        filtered_versions = UploadsVersion.objects.folder_viewable(folder_pk=self.folder_1.pk)

        # Verify that only versions with datasets in the specified folder are returned
        assert filtered_versions.count() == 1
        assert filtered_versions.first().pk == version_with_dataset.pk

        # Verify that the version without dataset is excluded
        version_pks = [v.pk for v in filtered_versions]
        assert version_without_dataset.pk not in version_pks


@pytest.mark.django_db
class TestUploadsVersionLockStatusMixin:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        self.project_1 = Project.objects.create(
            name="Project 1",
        )

        self.dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
            folder=self.project_1.folders.first(),
        )

        self.uploads_version_1 = UploadsVersion.objects.create(
            dataset=self.dataset_1,
        )

    def test_lock(self, client, initial_users):
        """
        Ensure we have an expected lock behavior.
        """
        set_request_for_user(initial_users["user_1"])

        url = reverse(
            "uploads-dataset-detail",
            kwargs={
                "pk": self.dataset_1.pk,
            },
        )

        lock_url = f"{url}lock/"
        unlock_url = f"{url}unlock/"
        status_url = f"{url}status/"

        uploads_version_url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )

        uploads_version_status_url = f"{url}status/"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.patch(
            url,
            {
                "name": "Dataset 1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dataset 1"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        last_lock_time = response.data["locked_at"]

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None
        assert response.data["locked_at"] > last_lock_time

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None
        assert response.data["locked_at"] > last_lock_time

        response = client.patch(
            url,
            {
                "name": "Dataset 1 - Edit #1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dataset 1 - Edit #1"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        auth_user(client, initial_users["user_2"])

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        response = client.get(uploads_version_url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        assert self.project_1.members_count == 1
        assert self.project_1.folders.first().members_count == 1

        ProjectMembership.objects.create(
            project=self.project_1,
            member=initial_users["user_2"],
            is_project_admin=True,
        )

        assert self.project_1.members_count == 2
        assert self.project_1.folders.first().members_count == 2

        folder_permission = FolderPermission.objects.get(
            project_membership__member=initial_users["user_2"],
            folder=self.project_1.folders.first(),
        )
        assert folder_permission.is_folder_admin is True
        assert folder_permission.is_metadata_template_admin is True
        assert folder_permission.can_edit is True

        response = client.patch(
            url,
            {
                "name": "Dataset 1 - Edit #3",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Dataset 1 - Edit #3"

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_2"].pk
        assert response.data["locked_at"] is not None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_2"].pk
        assert response.data["locked_at"] is not None

        auth_user(client, initial_users["user_1"])

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        auth_user(client, initial_users["user_2"])

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        auth_user(client, initial_users["user_1"])

        response = client.post(
            lock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is True
        assert response.data["locked_by"]["pk"] == initial_users["user_1"].pk
        assert response.data["locked_at"] is not None

        response = client.post(
            unlock_url,
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        response = client.get(status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None

        response = client.get(uploads_version_status_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["locked"] is False
        assert response.data["locked_by"] is None
        assert response.data["locked_at"] is None


@pytest.mark.django_db
class TestUploadsVersionFileAPI:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        self.uploads_version_1 = UploadsVersion.objects.create(
            version_file=self.uploads_version_file_1,
        )

    def test_read_uploads_version_file_details(self, client):
        """
        Ensure we can read the uploads version file details.
        """
        url = reverse(
            "uploads-version-file-detail",
            kwargs={
                "pk": self.uploads_version_file_1.pk,
            },
        )

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == self.uploads_version_file_1.name


@pytest.mark.django_db
class TestUploadsVersionMetadataAPI:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.uploads_version_1 = UploadsVersion.objects.create()

        self.uploads_version_2 = UploadsVersion.objects.create()

        set_metadata(
            assigned_to_content_type=self.uploads_version_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_1.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

    def test_read_uploads_version_metadata_list(self, client):
        """
        Ensure we can read the uploads version metadata list.
        """
        url = reverse("metadata-list")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

        url_filter = (
            f"{url}?assigned_to_content_type={get_content_type_for_object(self.uploads_version_1.get_content_type())}"
            f"&assigned_to_object_id={self.uploads_version_1.pk}"
        )
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        url_filter = (
            f"{url}?assigned_to_content_type={get_content_type_for_object(self.uploads_version_2.get_content_type())}"
            f"&assigned_to_object_id={self.uploads_version_2.pk}"
        )
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


@pytest.mark.django_db
class TestUploadsVersionFileMetadataAPI:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        self.uploads_version_file_2 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        self.uploads_version_file_metadata_1 = set_metadata(
            assigned_to_content_type=self.uploads_version_file_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_file_1.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

    def test_read_uploads_version_file_metadata_list(self, client):
        """
        Ensure we can read the uploads version file metadata list.
        """
        url = reverse("metadata-list")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

        url_filter = (
            f"{url}?assigned_to_content_type={get_content_type_for_object(self.uploads_version_file_1.get_content_type())}"
            f"&assigned_to_object_id={self.uploads_version_file_1.pk}"
        )
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        url_filter = (
            f"{url}?assigned_to_content_type={get_content_type_for_object(self.uploads_version_file_2.get_content_type())}"
            f"&assigned_to_object_id={self.uploads_version_file_2.pk}"
        )
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


@pytest.mark.django_db
class TestListUploadsVersionInFolderAPI:
    @pytest.fixture(autouse=True)
    def _setup(self, client, initial_users):
        set_request_for_user(initial_users["tum_member_user"])
        # Create a project
        project = Project.objects.create(
            name="Project Name",
        )

        # get the auto created "General" folder
        self.general_folder = Folder.objects.get(project=project.pk)

        # Add a regular project member, who will have folder permissions
        project_membership_1 = ProjectMembership.objects.create(
            member=initial_users["regular_user"],
            project=project,
        )
        FolderPermission.objects.create(
            folder=self.general_folder,
            project_membership=project_membership_1,
            is_folder_admin=False,
            can_edit=False,
        )

        # Add another regular project member, who will not have folder permissions
        ProjectMembership.objects.create(
            member=initial_users["regular_user_2"],
            project=project,
        )

        # create 4, 2 and 1 datasets with upload_versions created_by 3 different users and link them with the
        # general_folder, except the first version of the member user which is not linked to a folder and not published
        uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset tum_member_user 1",
        )
        UploadsVersion.objects.create(
            dataset=uploads_dataset_1,
        )

        self.general_folder.unlock()
        uploads_dataset_2 = UploadsDataset.objects.create(
            name="Dataset tum_member_user 2",
            folder=self.general_folder,
        )
        UploadsVersion.objects.create(
            dataset=uploads_dataset_2,
            publication_date=timezone.now(),
        )

        uploads_dataset_3 = UploadsDataset.objects.create(
            name="Dataset tum_member_user 3",
            folder=self.general_folder,
        )
        UploadsVersion.objects.create(
            dataset=uploads_dataset_3,
            publication_date=timezone.now(),
        )

        uploads_dataset_4 = UploadsDataset.objects.create(
            name="Dataset tum_member_user 4",
            folder=self.general_folder,
        )
        UploadsVersion.objects.create(
            dataset=uploads_dataset_4,
            publication_date=timezone.now(),
        )

        self.general_folder.unlock()
        set_request_for_user(initial_users["regular_user"])
        uploads_dataset_5 = UploadsDataset.objects.create(
            name="Dataset regular_user 1",
            folder=self.general_folder,
        )
        UploadsVersion.objects.create(
            dataset=uploads_dataset_5,
            publication_date=timezone.now(),
        )

        uploads_dataset_6 = UploadsDataset.objects.create(
            name="Dataset regular_user 2",
            folder=self.general_folder,
        )
        UploadsVersion.objects.create(
            dataset=uploads_dataset_6,
            publication_date=timezone.now(),
        )

        self.general_folder.unlock()
        set_request_for_user(initial_users["regular_user_2"])
        uploads_dataset_7 = UploadsDataset.objects.create(
            name="Dataset regular_user_2 3",
            folder=self.general_folder,
        )
        UploadsVersion.objects.create(
            dataset=uploads_dataset_7,
            publication_date=timezone.now(),
        )

    def test_list_uploads_version_with_valid_folder(self, client, initial_users):
        """
        Ensure users with the appropriate permissions can read versions in a folder
        """
        auth_user(client, initial_users["tum_member_user"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 6 published versions in this folder for this user
        assert len(response.data["results"]) == 6
        assert response.data["count"] == 6

        auth_user(client, initial_users["regular_user"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 6 published versions in this folder for this user
        assert len(response.data["results"]) == 6
        assert response.data["count"] == 6

    def test_list_uploads_version_with_valid_folder_no_permissions(self, client, initial_users):
        """
        Ensure users without appropriate permissions get no results for a valid folder
        """
        auth_user(client, initial_users["regular_user_2"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 0 published versions in this folder for this user
        assert len(response.data["results"]) == 0
        assert response.data["count"] == 0

    def test_list_uploads_version_with_invalid_folder(self, client, initial_users):
        """
        Ensure invalid folders give a invalid_choice error 400
        """
        auth_user(client, initial_users["tum_member_user"])
        url = reverse("uploads-version-list")
        invalid_uuid = uuid.uuid4()
        url_filter = f"{url}?dataset__folder={invalid_uuid}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["dataset__folder"][0].code == "invalid_choice"

    def test_list_uploads_version_with_valid_folder_and_another_filter(self, client, initial_users):
        """
        Ensure users with appropriate permissions can read versions in a folder with another filter on top
        """
        auth_user(client, initial_users["regular_user"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}&created_by={initial_users['tum_member_user'].pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 3 published versions in this folder created_by this user
        assert len(response.data["results"]) == 3
        assert response.data["count"] == 3

        auth_user(client, initial_users["regular_user"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}&created_by={initial_users['regular_user'].pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 2 published versions in this folder created_by this user
        assert len(response.data["results"]) == 2
        assert response.data["count"] == 2

        auth_user(client, initial_users["regular_user"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}&created_by={initial_users['regular_user_2'].pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 1 published versions in this folder created_by this user
        assert len(response.data["results"]) == 1
        assert response.data["count"] == 1


@pytest.mark.django_db
class TestViewDetailUploadsVersionInFolderAPI:
    @pytest.fixture(autouse=True)
    def _setup(self, client, initial_users):
        set_request_for_user(initial_users["tum_member_user"])

        project = Project.objects.create(
            name="Project Name",
        )

        self.general_folder = project.folders.first()

        project_membership_1 = ProjectMembership.objects.create(
            member=initial_users["regular_user"],
            project=project,
        )

        FolderPermission.objects.create(
            folder=self.general_folder,
            project_membership=project_membership_1,
            is_folder_admin=False,
            can_edit=True,
        )

        ProjectMembership.objects.create(
            member=initial_users["regular_user_2"],
            project=project,
        )

        set_request_for_user(initial_users["regular_user"])

        self.uploads_version_draft_1 = UploadsVersion.objects.create()

        self.uploads_version_draft_2 = UploadsVersion.objects.create()

        self.uploads_version_draft_3 = UploadsVersion.objects.create()

        self.uploads_version_in_folder_1 = UploadsVersion.objects.create(
            publication_date=timezone.now(),
        )
        self.uploads_version_in_folder_1.dataset.folder = self.general_folder
        self.uploads_version_in_folder_1.dataset.publication_date = timezone.now()
        self.uploads_version_in_folder_1.dataset.save()

        self.uploads_version_in_folder_2 = UploadsVersion.objects.create(
            publication_date=timezone.now(),
        )
        self.uploads_version_in_folder_2.dataset.folder = self.general_folder
        self.uploads_version_in_folder_2.dataset.publication_date = timezone.now()
        self.uploads_version_in_folder_2.dataset.save()

    def test_list_uploads_dataset_drafts(self, client, initial_users):
        """
        Ensure each user can read the list for datasets uploaded by themselves (draft files).
        """

        auth_user(client, initial_users["regular_user"])
        url = reverse("uploads-dataset-list")
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

        auth_user(client, initial_users["tum_member_user"])
        url = reverse("uploads-dataset-list")
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

        auth_user(client, initial_users["regular_user_2"])
        url = reverse("uploads-dataset-list")
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_list_uploads_version_with_valid_folder(self, client, initial_users):
        """
        Ensure users with the appropriate permissions can read versions in a folder
        """
        auth_user(client, initial_users["tum_member_user"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 2 published versions in this folder for this user
        assert len(response.data["results"]) == 2
        assert response.data["count"] == 2

        auth_user(client, initial_users["regular_user"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 2 published versions in this folder for this user
        assert len(response.data["results"]) == 2
        assert response.data["count"] == 2

        auth_user(client, initial_users["regular_user_2"])
        url = reverse("uploads-version-list")
        url_filter = f"{url}?dataset__folder={self.general_folder.pk}"
        response = client.get(url_filter, format="json")
        assert response.status_code == status.HTTP_200_OK
        # there should be 0 published versions in this folder for this user
        assert len(response.data["results"]) == 0
        assert response.data["count"] == 0

    def test_view_uploads_version_detail_in_draft(self, client, initial_users):
        """
        Ensure users read versions details of their own drafts
        """
        auth_user(client, initial_users["tum_member_user"])
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_draft_1.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        auth_user(client, initial_users["regular_user"])
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_published"] is False

        auth_user(client, initial_users["regular_user"])
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_draft_2.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_published"] is False

    def test_view_uploads_version_detail_in_folder(self, client, initial_users):
        """
        Ensure users with the appropriate permissions can read versions details in a folder
        """
        auth_user(client, initial_users["tum_member_user"])
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_in_folder_1.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_published"] is True

        auth_user(client, initial_users["regular_user"])
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_published"] is True

        auth_user(client, initial_users["regular_user_2"])
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        auth_user(client, initial_users["tum_member_user"])
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_in_folder_2.pk,
            },
        )
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_published"] is True

        auth_user(client, initial_users["regular_user"])
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_published"] is True

        auth_user(client, initial_users["regular_user_2"])
        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestUploadsVersionDiffAPI:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        storage_1 = DynamicStorage.objects.get(
            default=True,
        )

        self.project_1 = Project.objects.create(
            name="Project 1",
        )

        self.folder_1 = self.project_1.folders.first()
        self.folder_1.storage = storage_1
        self.folder_1.save()

        self.uploads_version_file_1 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        self.uploads_dataset_1 = UploadsDataset.objects.create(
            name="Dataset 1",
        )

        self.uploads_version_1 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=self.uploads_version_file_1,
        )

        self.uploads_version_file_2 = UploadsVersionFile.objects.create(
            uploaded_file=sample_file2,
        )

        self.uploads_version_2 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=self.uploads_version_file_2,
        )

        self.metadata_1 = set_metadata(
            assigned_to_content_type=self.uploads_version_2.get_content_type(),
            assigned_to_object_id=self.uploads_version_2.pk,
            custom_key="custom_key_1",
            value="custom_value_1",
        )

        self.metadata_2 = set_metadata(
            assigned_to_content_type=self.uploads_version_2.get_content_type(),
            assigned_to_object_id=self.uploads_version_2.pk,
            custom_key="custom_key_2",
            value="custom_value_2",
        )

        self.uploads_version_3 = UploadsVersion.objects.create(
            dataset=self.uploads_dataset_1,
            version_file=self.uploads_version_file_1,
        )

    def test_diff_successful(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_2.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "metadata" in response.data
        assert "version_file" in response.data

    def test_diff_missing_compare_parameter(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(action_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["compare"] == "You must provide an uploads version to compare to."

    def test_diff_invalid_uuid_format(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": "invalid-uuid",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["compare"] == "Invalid UUID format for compare parameter."

    def test_diff_non_existent_compare_version(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )
        action_url = f"{url}diff/"

        non_existent_uuid = uuid.uuid4()

        response = client.get(
            action_url,
            {
                "compare": str(non_existent_uuid),
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["compare"] == "An uploads version with this primary key does not exist."

    def test_diff_identical_versions(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_3.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "metadata" not in response.data
        assert "version_file" not in response.data
        assert "version" in response.data

    def test_diff_versions(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_2.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "version" in response.data
        assert response.data["version"]["old"]["pk"] == str(self.uploads_version_1.pk)
        assert response.data["version"]["old"]["name"] == self.uploads_version_1.name
        assert response.data["version"]["new"]["pk"] == str(self.uploads_version_2.pk)
        assert response.data["version"]["new"]["name"] == self.uploads_version_2.name
        assert response.data["version"]["new"]["creation_date"] > response.data["version"]["old"]["creation_date"]

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_2.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_1.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "version" in response.data
        assert response.data["version"]["old"]["pk"] == str(self.uploads_version_1.pk)
        assert response.data["version"]["old"]["name"] == self.uploads_version_1.name
        assert response.data["version"]["new"]["pk"] == str(self.uploads_version_2.pk)
        assert response.data["version"]["new"]["name"] == self.uploads_version_2.name
        assert response.data["version"]["new"]["creation_date"] > response.data["version"]["old"]["creation_date"]

    def test_diff_metadata(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_2.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_1.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "metadata" in response.data
        assert len(response.data["metadata"]) == 2
        assert {
            "key": self.metadata_1.custom_key,
            "old": None,
            "new": self.metadata_1.get_value(),
        } in response.data["metadata"]
        assert {
            "key": self.metadata_2.custom_key,
            "old": None,
            "new": self.metadata_2.get_value(),
        } in response.data["metadata"]

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_3.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_2.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "metadata" in response.data
        assert len(response.data["metadata"]) == 2
        assert {
            "key": self.metadata_1.custom_key,
            "old": self.metadata_1.get_value(),
            "new": None,
        } in response.data["metadata"]
        assert {
            "key": self.metadata_2.custom_key,
            "old": self.metadata_2.get_value(),
            "new": None,
        } in response.data["metadata"]

    def test_diff_version_file(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_2.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_1.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "version_file" in response.data
        assert response.data["version_file"]["old"]["pk"] == str(self.uploads_version_1.version_file.pk)
        assert response.data["version_file"]["old"]["name"] == self.uploads_version_1.version_file.name
        assert response.data["version_file"]["new"]["pk"] == str(self.uploads_version_2.version_file.pk)
        assert response.data["version_file"]["new"]["name"] == self.uploads_version_2.version_file.name

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_3.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_2.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "version_file" in response.data
        assert response.data["version_file"]["old"]["pk"] == str(self.uploads_version_2.version_file.pk)
        assert response.data["version_file"]["old"]["name"] == self.uploads_version_2.version_file.name
        assert response.data["version_file"]["new"]["pk"] == str(self.uploads_version_3.version_file.pk)
        assert response.data["version_file"]["new"]["name"] == self.uploads_version_3.version_file.name

    def test_diff_metadata_old_new_sorting(self, client):
        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_2.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_1.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "metadata" in response.data
        assert len(response.data["metadata"]) == 2
        assert {
            "key": self.metadata_1.custom_key,
            "old": None,
            "new": self.metadata_1.get_value(),
        } in response.data["metadata"]
        assert {
            "key": self.metadata_2.custom_key,
            "old": None,
            "new": self.metadata_2.get_value(),
        } in response.data["metadata"]

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_1.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_2.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "metadata" in response.data
        assert len(response.data["metadata"]) == 2
        assert {
            "key": self.metadata_1.custom_key,
            "old": None,
            "new": self.metadata_1.get_value(),
        } in response.data["metadata"]
        assert {
            "key": self.metadata_2.custom_key,
            "old": None,
            "new": self.metadata_2.get_value(),
        } in response.data["metadata"]

    def test_diff_metadata_old_new_values(self, client):
        metadata_3 = set_metadata(
            assigned_to_content_type=self.uploads_version_3.get_content_type(),
            assigned_to_object_id=self.uploads_version_3.pk,
            custom_key=self.metadata_2.custom_key,
            value="custom_value_3",
        )

        url = reverse(
            "uploads-version-detail",
            kwargs={
                "pk": self.uploads_version_3.pk,
            },
        )
        action_url = f"{url}diff/"

        response = client.get(
            action_url,
            {
                "compare": str(self.uploads_version_2.pk),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "metadata" in response.data
        assert len(response.data["metadata"]) == 2
        assert {
            "key": self.metadata_1.custom_key,
            "old": self.metadata_1.get_value(),
            "new": None,
        } in response.data["metadata"]
        assert {
            "key": self.metadata_2.custom_key,
            "old": self.metadata_2.get_value(),
            "new": metadata_3.get_value(),
        } in response.data["metadata"]
