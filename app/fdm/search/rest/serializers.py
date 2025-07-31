from rest_framework import serializers

from fdm.folders.rest.serializers import FolderSearchSerializer
from fdm.projects.rest.serializers import ProjectSearchSerializer
from fdm.uploads.rest.serializers import UploadsDatasetSearchSerializer, UploadsVersionSearchSerializer

__all__ = [
    "SearchSerializer",
]


class SearchSerializer(serializers.Serializer):
    projects = ProjectSearchSerializer(many=True)

    folders = FolderSearchSerializer(many=True)

    uploads_datasets = UploadsDatasetSearchSerializer(many=True)

    uploads_versions = UploadsVersionSearchSerializer(many=True)
