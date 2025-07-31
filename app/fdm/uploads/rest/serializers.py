from rest_framework import serializers

from drf_spectacular.utils import extend_schema, extend_schema_field

from fdm.core.rest.base import BaseModelSerializer
from fdm.core.rest.serializers import BaseModelWithByUserSerializer
from fdm.folders.rest.serializers import FolderBidirectionalSerializer, FolderSearchSerializer, FolderSerializer
from fdm.metadata.rest.serializers import MetadataPayloadSerializer, MinimalMetadataSerializer
from fdm.uploads.models import *

__all__ = [
    "UploadsVersionStatusSerializer",
    "UploadsVersionsForUploadsDatasetListSerializer",
    "MinimalUploadsVersionFileSerializer",
    "MinimalUploadsVersionFileSearchSerializer",
    "MinimalUploadsVersionFileDiffSerializer",
    "MinimalFlatUploadsVersionSerializer",
    "UploadsVersionsForUploadsDatasetSerializer",
    "MinimalUploadsVersionSerializer",
    "MinimalUploadsDatasetSerializer",
    "UploadsDatasetSerializer",
    "UploadsDatasetCreatePayloadSerializer",
    "UploadsDatasetCreateSerializer",
    "UploadsDatasetUpdatePayloadSerializer",
    "UploadsDatasetUpdateSerializer",
    "UploadsDatasetBulkDeleteSerializer",
    "UploadsDatasetListSerializer",
    "MinimalUploadsDatasetSearchSerializer",
    "UploadsVersionPayloadSerializer",
    "UploadsDatasetVersionActionPayloadSerializer",
    "UploadsVersionSerializer",
    "MinimalUploadsVersionSearchSerializer",
    "MinimalUploadsVersionDiffSerializer",
    "UploadsVersionSearchSerializer",
    "UploadsDatasetSearchSerializer",
    "UploadsVersionFileSerializer",
    "UploadsVersionFileSearchSerializer",
    "UploadsVersionDiffResponseSerializer",
    "DiffValueSerializer",
    "MetadataDiffValueSerializer",
    "UploadsVersionFileDiffSerializer",
    "UploadsVersionDiffResponseSerializer",
]


@extend_schema_field(
    {
        "type": "string",
        "enum": [choice[0] for choice in UploadsVersion.Status.choices],
    },
)
class UploadsVersionStatusSerializer(serializers.Serializer):
    pass


class UploadsVersionsForUploadsDatasetListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.order_by(
            "-creation_date",
        )
        return super().to_representation(data)


class MinimalUploadsVersionFileSerializer(BaseModelWithByUserSerializer):
    metadata = MinimalMetadataSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = UploadsVersionFile
        fields = [
            "pk",
            "name",
            "status",
            "storage_relocating",
            "is_published",
            "publication_date",
            "metadata",
            "is_referenced",
        ]


class MinimalUploadsVersionFileSearchSerializer(BaseModelWithByUserSerializer):
    class Meta:
        model = UploadsVersionFile
        fields = [
            "pk",
            "name",
        ]


class MinimalUploadsVersionFileDiffSerializer(BaseModelSerializer):
    class Meta:
        model = UploadsVersionFile
        fields = [
            "pk",
            "name",
        ]


class MinimalFlatUploadsVersionSerializer(BaseModelSerializer):
    class Meta:
        model = UploadsVersion
        fields = [
            "pk",
            "dataset",
        ]


class UploadsVersionsForUploadsDatasetSerializer(BaseModelSerializer):
    class Meta:
        model = UploadsVersion
        list_serializer_class = UploadsVersionsForUploadsDatasetListSerializer
        fields = [
            "pk",
            "name",
            "creation_date",
            "is_published",
            "publication_date",
        ]


class MinimalUploadsVersionSerializer(BaseModelSerializer):
    version_file = MinimalUploadsVersionFileSerializer(
        read_only=True,
    )

    class Meta:
        model = UploadsVersion
        fields = [
            "pk",
            "name",
            "version_file",
            "creation_date",
        ]


class MinimalUploadsDatasetSerializer(BaseModelSerializer):
    class Meta:
        model = UploadsDataset
        fields = [
            "pk",
            "name",
            "display_name",
        ]


class UploadsDatasetSerializer(BaseModelWithByUserSerializer):
    folder = FolderSerializer(
        required=False,
        allow_null=True,
    )

    uploads_versions = UploadsVersionsForUploadsDatasetSerializer(
        many=True,
        read_only=True,
    )

    latest_version = MinimalUploadsVersionSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UploadsDataset
        fields = [
            "pk",
            "name",
            "display_name",
            "folder",
            "uploads_versions",
            "latest_version",
            "is_published",
            "publication_date",
            "is_expired",
            "expiry_date",
        ]


class UploadsDatasetCreatePayloadSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        allow_null=True,
    )

    folder = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class UploadsDatasetCreateSerializer(BaseModelWithByUserSerializer):
    folder = FolderBidirectionalSerializer(
        required=False,
        allow_null=True,
    )

    uploads_versions = UploadsVersionsForUploadsDatasetSerializer(
        many=True,
        read_only=True,
    )

    latest_version = MinimalUploadsVersionSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UploadsDataset

        fields = [
            "name",
            "folder",
            "uploads_versions",
            "latest_version",
            "is_published",
            "publication_date",
            "is_expired",
            "expiry_date",
        ]

    def create(self, validated_data):
        return UploadsDataset.objects.create(**validated_data)


class UploadsDatasetUpdatePayloadSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        allow_null=True,
    )


class UploadsDatasetUpdateSerializer(BaseModelWithByUserSerializer):
    folder = FolderBidirectionalSerializer(
        required=False,
        allow_null=True,
    )

    uploads_versions = UploadsVersionsForUploadsDatasetSerializer(
        many=True,
        read_only=True,
    )

    latest_version = MinimalUploadsVersionSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UploadsDataset

        fields = [
            "name",
            "folder",
            "uploads_versions",
            "latest_version",
            "is_published",
            "publication_date",
            "is_expired",
            "expiry_date",
        ]

    def create(self, validated_data):
        return UploadsDataset.objects.create(**validated_data)

    def update(self, instance, validated_data):
        try:
            validated_data.pop("folder")
        except KeyError:
            pass

        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()

        return instance

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class UploadsDatasetBulkDeleteSerializer(serializers.Serializer):
    success = serializers.ListSerializer(
        child=serializers.UUIDField(),
        required=True,
    )

    error = serializers.ListSerializer(
        child=serializers.UUIDField(),
        required=True,
    )


class UploadsDatasetListSerializer(BaseModelWithByUserSerializer):
    folder = FolderSearchSerializer(
        required=False,
        allow_null=True,
    )

    uploads_versions = UploadsVersionsForUploadsDatasetSerializer(
        many=True,
        read_only=True,
    )

    latest_version = MinimalUploadsVersionSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UploadsDataset
        fields = [
            "pk",
            "name",
            "display_name",
            "folder",
            "uploads_versions",
            "latest_version",
            "is_published",
            "publication_date",
            "is_expired",
            "expiry_date",
        ]


class MinimalUploadsDatasetSearchSerializer(BaseModelWithByUserSerializer):
    class Meta:
        model = UploadsDataset
        fields = [
            "pk",
            "name",
            "display_name",
        ]


class MinimalUploadsDatasetWithFolderSearchSerializer(BaseModelWithByUserSerializer):
    folder = FolderSearchSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UploadsDataset
        fields = [
            "pk",
            "name",
            "folder",
        ]


class UploadsVersionPayloadSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        allow_null=True,
    )

    status = UploadsVersionStatusSerializer(
        required=False,
    )


class UploadsDatasetVersionActionPayloadSerializer(serializers.Serializer):
    metadata = MetadataPayloadSerializer(
        required=False,
    )


class UploadsVersionSerializer(BaseModelWithByUserSerializer):
    metadata = MinimalMetadataSerializer(
        many=True,
        required=False,
    )

    dataset = MinimalUploadsDatasetSerializer(
        read_only=True,
    )

    version_file = MinimalUploadsVersionFileSerializer(
        read_only=True,
    )

    class Meta:
        model = UploadsVersion
        fields = [
            "pk",
            "name",
            "dataset",
            "version_file",
            "is_published",
            "publication_date",
            "metadata_is_complete",
            "metadata",
            "status",
        ]

    @extend_schema(
        request=UploadsVersionPayloadSerializer,
    )
    def update(self, instance, validated_data):
        for key in list(validated_data.keys()):
            if key not in ["name", "status"]:
                del validated_data[key]

        return super().update(instance, validated_data)

    @extend_schema(
        request=UploadsVersionPayloadSerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class MinimalUploadsVersionSearchSerializer(BaseModelWithByUserSerializer):
    version_file = MinimalUploadsVersionFileSearchSerializer(
        required=True,
    )

    class Meta:
        model = UploadsVersion
        fields = [
            "pk",
            "name",
            "version_file",
            "creation_date",
        ]


class MinimalUploadsVersionDiffSerializer(BaseModelSerializer):
    class Meta:
        model = UploadsVersion
        fields = [
            "pk",
            "name",
            "creation_date",
        ]


class UploadsVersionSearchSerializer(BaseModelWithByUserSerializer):
    dataset = MinimalUploadsDatasetWithFolderSearchSerializer()

    version_file = MinimalUploadsVersionFileSearchSerializer(
        required=True,
    )

    class Meta:
        model = UploadsVersion
        fields = [
            "pk",
            "name",
            "dataset",
            "version_file",
        ]


class UploadsDatasetSearchSerializer(BaseModelWithByUserSerializer):
    folder = FolderSearchSerializer(
        required=False,
        allow_null=True,
    )

    latest_version = MinimalUploadsVersionSearchSerializer(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UploadsDataset
        fields = [
            "pk",
            "name",
            "display_name",
            "folder",
            "latest_version",
        ]


class UploadsVersionFileSerializer(BaseModelWithByUserSerializer):
    metadata = MinimalMetadataSerializer(
        many=True,
        read_only=True,
    )

    uploads_versions = MinimalFlatUploadsVersionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = UploadsVersionFile
        fields = [
            "pk",
            "uploads_versions",
            "name",
            "status",
            "storage_relocating",
            "is_published",
            "publication_date",
            "metadata",
            "is_referenced",
        ]


class UploadsVersionFileSearchSerializer(BaseModelWithByUserSerializer):
    class Meta:
        model = UploadsVersionFile
        fields = [
            "pk",
            "uploads_versions",
            "name",
        ]


class DiffValueSerializer(serializers.Serializer):
    old = serializers.CharField(
        allow_null=True,
    )

    new = serializers.CharField(
        allow_null=True,
    )


class MetadataDiffValueSerializer(serializers.Serializer):
    key = serializers.CharField(
        required=True,
        allow_null=False,
    )

    old = serializers.CharField(
        allow_null=True,
    )

    new = serializers.CharField(
        allow_null=True,
    )


# TODO: In the future it should be possible to have versions without files. We'll need to change this then.
class UploadsVersionFileDiffSerializer(serializers.Serializer):
    old = MinimalUploadsVersionFileDiffSerializer(
        required=True,
        allow_null=False,
    )

    new = MinimalUploadsVersionFileDiffSerializer(
        required=True,
        allow_null=False,
    )


class UploadsVersionDiffSerializer(serializers.Serializer):
    old = MinimalUploadsVersionDiffSerializer(
        required=True,
        allow_null=False,
    )

    new = MinimalUploadsVersionDiffSerializer(
        required=True,
        allow_null=False,
    )


class UploadsVersionDiffResponseSerializer(serializers.Serializer):
    metadata = serializers.ListSerializer(
        child=MetadataDiffValueSerializer(),
        read_only=True,
        required=False,
    )

    version_file = UploadsVersionFileDiffSerializer(
        required=False,
    )

    version = UploadsVersionDiffSerializer(
        required=True,
    )
