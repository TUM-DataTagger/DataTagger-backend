from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from rest_framework import status

import pytest

from fdm.core.helpers import set_request_for_user
from fdm.metadata.helpers import set_metadata
from fdm.projects.models import Project
from fdm.uploads.models import UploadsDataset, UploadsVersion, UploadsVersionFile

sample_file = SimpleUploadedFile(
    "file.jpg",
    b"",
    content_type="image/jpg",
)


@pytest.mark.django_db
class TestSearchAPI:
    @pytest.fixture(autouse=True)
    def _setup(self, initial_users):
        set_request_for_user(initial_users["user_1"])

        self.project_1 = Project.objects.create(
            name="Project 1",
        )

        set_metadata(
            assigned_to_content_type=self.project_1.get_content_type(),
            assigned_to_object_id=self.project_1.pk,
            custom_key="custom_project_key_1",
            value="custom_project_value_1",
        )

        self.folder_1 = self.project_1.folders.first()

        set_metadata(
            assigned_to_content_type=self.folder_1.get_content_type(),
            assigned_to_object_id=self.folder_1.pk,
            custom_key="custom_folder_key_1",
            value="custom_folder_value_1",
        )

        self.uploads_dataset_1 = UploadsDataset.objects.create(
            name="Custom dataset 1",
            folder=self.folder_1,
        )

        self.uploads_version_1 = UploadsVersion.objects.create(
            name="Uploads version 1",
            dataset=self.uploads_dataset_1,
        )

        self.uploads_version_metadata_1 = set_metadata(
            assigned_to_content_type=self.uploads_version_1.get_content_type(),
            assigned_to_object_id=self.uploads_version_1.pk,
            custom_key="custom_uploads_version_key_1",
            value="custom_uploads_version_value_1",
        )

        self.project_2 = Project.objects.create(
            name="Project 2",
        )

        self.folder_2 = self.project_2.folders.first()
        self.folder_2.name = "Folder 2"
        self.folder_2.save()

        set_metadata(
            assigned_to_content_type=self.project_2.get_content_type(),
            assigned_to_object_id=self.project_2.pk,
            custom_key="custom_project_key_2",
            value="custom_project_value_2",
        )

        set_metadata(
            assigned_to_content_type=self.project_2.folders.first().get_content_type(),
            assigned_to_object_id=self.project_2.folders.first().pk,
            custom_key="custom_folder_key_2",
            value="custom_folder_value_2",
        )

        self.uploads_dataset_2 = UploadsDataset.objects.create(
            name="Dataset 2",
            folder=self.project_2.folders.first(),
        )

        uploads_version_file = UploadsVersionFile.objects.create(
            uploaded_file=sample_file,
        )

        set_metadata(
            assigned_to_content_type=uploads_version_file.get_content_type(),
            assigned_to_object_id=uploads_version_file.pk,
            custom_key="custom_uploads_version_file_key_1",
            value="custom_uploads_version_file_value_1",
        )

        self.uploads_version_2 = UploadsVersion.objects.create(
            name="Uploads version 2",
            dataset=self.uploads_dataset_2,
            version_file=uploads_version_file,
        )

        self.uploads_dataset_3 = UploadsDataset.objects.create(
            name="Dataset 3",
        )

        self.uploads_version_3 = UploadsVersion.objects.create(
            name="Uploads version 3",
            dataset=self.uploads_dataset_3,
        )

        set_metadata(
            assigned_to_content_type=self.uploads_version_3.get_content_type(),
            assigned_to_object_id=self.uploads_version_3.pk,
            custom_key="custom_uploads_version_key_3",
            value="custom_uploads_version_value_3",
        )

        self.project_3 = Project.objects.create(
            name="Project 3",
        )

        self.project_4 = Project.objects.create(
            name="Project 4",
        )

        self.project_5 = Project.objects.create(
            name="Project 5",
        )

        self.project_6 = Project.objects.create(
            name="Project 6",
        )

        self.project_7 = Project.objects.create(
            name="Project 7",
        )

        self.project_8 = Project.objects.create(
            name="Project 8",
        )

        self.project_9 = Project.objects.create(
            name="Project 9",
        )

        self.project_10 = Project.objects.create(
            name="Project A",
        )

        self.project_11 = Project.objects.create(
            name="Project B",
        )

    def test_read_search_results(self, client):
        """
        Ensure we can read the search results. The structure is as follows:

        === DRAFTS ===
        Dataset 3
        -> Uploads version 3 (Metadata: custom_uploads_version_key_3=custom_uploads_version_value_3)

        === PUBLIC ===
        Project 1 (Metadata: custom_project_key_1=custom_project_value_1)
        -> General (Metadata: custom_folder_key_1=custom_folder_value_1)
           -> Custom dataset 1
              -> Uploads version 1 (Metadata: custom_uploads_version_key_1=custom_uploads_version_value_1)
        Project 2 (Metadata: custom_project_key_2=custom_project_value_2)
        -> Folder 2 (Metadata: custom_folder_key_2=custom_folder_value_2)
           -> Dataset 2
              -> Uploads version 2
                 -> File (Metadata: custom_uploads_version_file_key_1=custom_uploads_version_file_value_1)
        Project 3
        -> General
        Project 4
        -> General
        Project 5
        -> General
        Project 6
        -> General
        Project 7
        -> General
        Project 8
        -> General
        Project 9
        -> General
        Project A
        -> General
        Project B
        -> General
        """
        url = reverse("search-global")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        action_url = f"{url}?term={self.project_1.name}"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 1
        assert response.data["projects"][0]["name"] == self.project_1.name
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=Project"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 5
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=Project&limit=20"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 11
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=Folder"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 2
        assert all(
            project["name"]
            in [
                self.project_1.name,
                self.project_2.name,
            ]
            for project in response.data["projects"]
        )
        assert len(response.data["folders"]) == 2
        assert all(
            folder["name"]
            in [
                self.folder_1.name,
                self.folder_2.name,
            ]
            for folder in response.data["folders"]
        )
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term={self.folder_2.name}"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 1
        assert response.data["projects"][0]["name"] == self.project_2.name
        assert len(response.data["folders"]) == 1
        assert response.data["folders"][0]["name"] == self.folder_2.name
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f'{url}?term={_("General")}&limit=20'
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 10
        assert all(
            project["name"]
            in [
                self.project_1.name,
                self.project_3.name,
                self.project_4.name,
                self.project_5.name,
                self.project_6.name,
                self.project_7.name,
                self.project_8.name,
                self.project_9.name,
                self.project_10.name,
                self.project_11.name,
            ]
            for project in response.data["projects"]
        )
        assert len(response.data["folders"]) == 10
        assert all(
            folder["name"]
            in [
                self.project_1.folders.first().name,
                self.project_3.folders.first().name,
                self.project_4.folders.first().name,
                self.project_5.folders.first().name,
                self.project_6.folders.first().name,
                self.project_7.folders.first().name,
                self.project_8.folders.first().name,
                self.project_9.folders.first().name,
                self.project_10.folders.first().name,
                self.project_11.folders.first().name,
            ]
            for folder in response.data["folders"]
        )
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term={self.project_2.folders.first().name}"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 1
        assert response.data["projects"][0]["name"] == self.project_2.name
        assert len(response.data["folders"]) == 1
        assert response.data["folders"][0]["name"] == self.folder_2.name
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=Dataset"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 2
        assert all(
            folder["name"]
            in [
                self.folder_1.name,
                self.folder_2.name,
            ]
            for folder in response.data["folders"]
        )
        assert len(response.data["uploads_datasets"]) == 3
        assert all(
            dataset["name"]
            in [
                self.uploads_dataset_1.name,
                self.uploads_dataset_2.name,
                self.uploads_dataset_3.name,
            ]
            for dataset in response.data["uploads_datasets"]
        )
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term={self.uploads_dataset_1.name}"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 1
        assert response.data["folders"][0]["name"] == self.folder_1.name
        assert len(response.data["uploads_datasets"]) == 1
        assert response.data["uploads_datasets"][0]["name"] == self.uploads_dataset_1.name
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=version"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 2
        assert all(
            folder["name"]
            in [
                self.folder_1.name,
                self.folder_2.name,
            ]
            for folder in response.data["folders"]
        )
        assert len(response.data["uploads_datasets"]) == 3
        assert all(
            uploads_dataset["name"]
            in [
                self.uploads_dataset_1.name,
                self.uploads_dataset_2.name,
                self.uploads_dataset_3.name,
            ]
            for uploads_dataset in response.data["uploads_datasets"]
        )
        assert len(response.data["uploads_versions"]) == 3
        assert all(
            uploads_version["name"]
            in [
                self.uploads_version_1.name,
                self.uploads_version_2.name,
                self.uploads_version_3.name,
            ]
            for uploads_version in response.data["uploads_versions"]
        )

        action_url = f"{url}?term={self.uploads_version_metadata_1.get_value()}"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 1
        assert response.data["folders"][0]["name"] == self.folder_1.name
        assert len(response.data["uploads_datasets"]) == 1
        assert response.data["uploads_datasets"][0]["name"] == self.uploads_dataset_1.name
        assert len(response.data["uploads_versions"]) == 1
        assert response.data["uploads_versions"][0]["name"] == self.uploads_version_1.name

        action_url = f"{url}?term=uploads_version"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 2
        assert all(
            folder["name"]
            in [
                self.folder_1.name,
                self.folder_2.name,
            ]
            for folder in response.data["folders"]
        )
        assert len(response.data["uploads_datasets"]) == 3
        assert all(
            uploads_dataset["name"]
            in [
                self.uploads_dataset_1.name,
                self.uploads_dataset_2.name,
                self.uploads_dataset_3.name,
            ]
            for uploads_dataset in response.data["uploads_datasets"]
        )
        assert len(response.data["uploads_versions"]) == 3
        assert all(
            uploads_version["name"]
            in [
                self.uploads_version_1.name,
                self.uploads_version_2.name,
                self.uploads_version_3.name,
            ]
            for uploads_version in response.data["uploads_versions"]
        )

        action_url = f"{url}?term=custom"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 2
        assert all(
            project["name"]
            in [
                self.project_1.name,
                self.project_2.name,
            ]
            for project in response.data["projects"]
        )
        assert len(response.data["folders"]) == 2
        assert all(
            folder["name"]
            in [
                self.folder_1.name,
                self.folder_2.name,
            ]
            for folder in response.data["folders"]
        )
        assert len(response.data["uploads_datasets"]) == 3
        assert all(
            uploads_dataset["name"]
            in [
                self.uploads_dataset_1.name,
                self.uploads_dataset_2.name,
                self.uploads_dataset_3.name,
            ]
            for uploads_dataset in response.data["uploads_datasets"]
        )
        assert len(response.data["uploads_versions"]) == 3
        assert all(
            uploads_version["name"]
            in [
                self.uploads_version_1.name,
                self.uploads_version_2.name,
                self.uploads_version_3.name,
            ]
            for uploads_version in response.data["uploads_versions"]
        )

        # Invalid usage of the limit parameter: negative limit turns into the default limit
        action_url = f"{url}?term=Project&limit=-1"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 5
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        # Invalid usage of the limit parameter: a value above the limit turns into the default limit
        action_url = f"{url}?term=Project&limit=21"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 5
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        # Filter by content types
        action_url = f"{url}?term=custom&limit=1&content_types=projects.project"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 1
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=custom&limit=1&content_types=folders.folder"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 1
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=custom&limit=1&content_types=uploads.uploadsdataset"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 1
        assert len(response.data["uploads_versions"]) == 0

        action_url = f"{url}?term=custom&limit=1&content_types=uploads.uploadsversion"
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 0
        assert len(response.data["folders"]) == 0
        assert len(response.data["uploads_datasets"]) == 0
        assert len(response.data["uploads_versions"]) == 1

        action_url = f"{url}?term=custom&limit=1&content_types=" + ",".join(
            [
                content_type
                for content_type in [
                    "projects.project",
                    "folders.folder",
                    "uploads.uploadsdataset",
                    "uploads.uploadsversion",
                ]
            ],
        )
        response = client.get(action_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["projects"]) == 1
        assert len(response.data["folders"]) == 1
        assert len(response.data["uploads_datasets"]) == 1
        assert len(response.data["uploads_versions"]) == 1
