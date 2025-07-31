import logging
import mimetypes
import os
import re
import uuid
from pathlib import Path
from wsgiref.handlers import format_date_time

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files import File
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_userforeignkey.request import get_current_user
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, inline_serializer

from fdm.core.rest.base import BaseModelViewSet
from fdm.core.rest.mixins import *
from fdm.core.rest.permissions import (
    CanCreateDataset,
    CanCreateDatasetVersion,
    CanDeleteDataset,
    CanEditInFolder,
    can_view_in_folder,
)
from fdm.file_parser.models import MimeTypeParser
from fdm.folders.models import Folder
from fdm.metadata.helpers import set_metadata, set_metadata_for_relation, validate_metadata
from fdm.metadata.models import Metadata
from fdm.rest_framework_tus.views import UploadViewSet as BaseTusUploadViewSet
from fdm.uploads.helpers import create_uploads_version_with_new_file_for_dataset
from fdm.uploads.models import *
from fdm.uploads.rest.serializers import *

__all__ = [
    "UploadsDatasetViewSet",
    "UploadsVersionViewSet",
    "UploadsVersionFileViewSet",
    "TusUploadViewSet",
]


logger = logging.getLogger(__name__)


class UploadsDatasetViewSet(
    BaseModelViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    LockStatusMixin,
    LockMixin,
    UnlockMixin,
):
    queryset = UploadsDataset.objects.none()

    serializer_class = UploadsDatasetSerializer

    serializer_action_classes = {
        "list": UploadsDatasetListSerializer,
        "create": UploadsDatasetCreateSerializer,
        "update": UploadsDatasetUpdateSerializer,
        "partial_update": UploadsDatasetUpdateSerializer,
    }

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "folder",
        "created_by",
        "last_modified_by",
    ]

    search_fields = [
        # Dataset fields
        "name",
        # Version fields
        "uploads_versions__name",
        "uploads_versions__metadata__custom_key",
        "uploads_versions__metadata__value",
        # Version file fields
        "uploads_versions__version_file__metadata__custom_key",
        "uploads_versions__version_file__metadata__value",
    ]

    ordering_fields = [
        "display_name",
        "creation_date",
        "expiry_date",
    ]

    permission_classes_by_action = {
        "create": [IsAuthenticated, CanCreateDataset],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "destroy": [IsAuthenticated, CanDeleteDataset],
        "version": [IsAuthenticated, CanCreateDatasetVersion],
        "restore": [IsAuthenticated, CanCreateDatasetVersion],
        "publish": [IsAuthenticated, CanEditInFolder],
    }

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()

    def get_permissions(self):
        return [permission() for permission in self.permission_classes_by_action.get(self.action, [])]

    def get_queryset(self):
        """
        Gets the queryset for the view set
        :return:
        """
        queryset = UploadsDataset.objects.all()
        folder_pk = self.request.query_params.get("folder", None)

        # Detail view of a dataset object
        if "pk" in self.kwargs:
            return queryset.my_viewable(view_type="detail")

        # Datasets in a specific folder
        if folder_pk:
            return queryset.folder_viewable(folder_pk=folder_pk)

        # Datasets in "My drafts"
        return queryset.my_viewable()

    @extend_schema(
        request=UploadsDatasetCreatePayloadSerializer,
        responses={
            201: UploadsDatasetSerializer,
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            UploadsDatasetSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(
        request=UploadsDatasetUpdatePayloadSerializer,
        responses={
            200: UploadsDatasetSerializer,
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request=UploadsDatasetUpdatePayloadSerializer,
        responses={
            200: UploadsDatasetSerializer,
        },
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter("ordering", exclude=True),
            OpenApiParameter("search", exclude=True),
        ],
        request=inline_serializer(
            name="UploadsDatasetBulkDeleteActionSerializer",
            fields={
                "uploads_datasets": serializers.ListSerializer(
                    child=serializers.UUIDField(),
                    required=True,
                ),
            },
        ),
        description=_("Deletes multiple uploads datasets in bulk."),
        responses={
            200: UploadsDatasetBulkDeleteSerializer,
        },
        methods=["POST"],
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="bulk-delete",
        url_name="bulk-delete",
        filterset_class=None,
        pagination_class=None,
    )
    def bulk_delete(self, request, *args, **kwargs):
        # Get all uploads datasets which should be deleted
        try:
            uploads_datasets = [
                UploadsDataset.objects.get(pk=uploads_dataset_pk)
                for uploads_dataset_pk in request.data.get("uploads_datasets", [])
            ]
        except UploadsDataset.DoesNotExist:
            return Response(
                data={
                    "uploads_datasets": _("At least one uploads dataset provided does not exist."),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not len(uploads_datasets):
            return Response(
                data={
                    "uploads_datasets": _("You must provide at least one uploads dataset."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if any([dataset.created_by != request.user for dataset in uploads_datasets]):
            return Response(
                data={
                    "uploads_datasets": _("You must not delete any uploads datasets you haven't created yourself."),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if any([dataset.is_published() for dataset in uploads_datasets]):
            return Response(
                data={
                    "uploads_datasets": _(
                        "You must not bulk delete uploads datasets containing already published items.",
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        results = {
            "success": [],
            "error": [],
        }

        for dataset in uploads_datasets:
            dataset_pk = dataset.pk

            try:
                dataset.delete()
                results["success"].append(dataset_pk)
            except Exception as e:
                logger.error(f"Could not delete uploads dataset {dataset}: {e}")
                results["error"].append(dataset_pk)

        return Response(
            data=UploadsDatasetBulkDeleteSerializer(results).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("ordering", exclude=True),
            OpenApiParameter("search", exclude=True),
        ],
        request=inline_serializer(
            name="UploadsDatasetBulkPublishActionSerializer",
            fields={
                "uploads_datasets": serializers.ListSerializer(
                    child=serializers.UUIDField(),
                    required=True,
                ),
                "folder": serializers.UUIDField(
                    required=True,
                ),
            },
        ),
        description=_("Publishes multiple uploads datasets in bulk into a folder."),
        responses={
            201: None,
        },
        methods=["POST"],
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="bulk-publish",
        url_name="bulk-publish",
        filterset_class=None,
        pagination_class=None,
    )
    def bulk_publish(self, request, *args, **kwargs):
        # Get all uploads datasets which should be published
        try:
            uploads_datasets = [
                UploadsDataset.objects.get(pk=uploads_dataset_pk)
                for uploads_dataset_pk in request.data.get("uploads_datasets", [])
            ]
        except UploadsDataset.DoesNotExist:
            return Response(
                data={
                    "uploads_datasets": _("At least one uploads dataset provided does not exist."),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not len(uploads_datasets):
            return Response(
                data={
                    "uploads_datasets": _("You must provide at least one uploads dataset."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            folder = Folder.objects.get(pk=request.data.get("folder"))
        except Folder.DoesNotExist:
            return Response(
                data={
                    "folder": _("A folder with this primary key does not exist."),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        for dataset in uploads_datasets:
            try:
                dataset.publish(folder=folder)
            except Exception as e:
                logger.error(f"Could not publish uploads dataset {dataset}: {e}")

        return Response(
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=inline_serializer(
            name="UploadsDatasetPublishActionSerializer",
            fields={
                "folder": serializers.UUIDField(
                    required=False,
                    allow_null=False,
                ),
            },
        ),
        responses={
            201: UploadsDatasetSerializer,
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="publish",
        url_name="publish",
        throttle_classes=[],
    )
    def publish(self, request, *args, **kwargs):
        dataset = self.get_object()

        dataset.publish(request.data.get("folder", None))

        return Response(
            data=UploadsDatasetSerializer(dataset).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=UploadsDatasetVersionActionPayloadSerializer,
        responses={
            201: UploadsVersionSerializer,
        },
        methods=["POST"],
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="version",
        url_name="version",
        filterset_class=None,
        pagination_class=None,
    )
    def version(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset = self.get_object()
        latest_version = dataset.latest_version
        metadata = None

        if dataset.locked and not dataset.is_locked_by_myself():
            return Response(
                data={
                    "lock": _("You must not edit an element which has been locked by another user."),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not latest_version:
            return Response(
                data={
                    "latest_version": _(
                        "You must create at least one version first before you can make requests to this endpoint.",
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # TODO: In the future it should be possible to have versions without files. We'll need to change this then.
        if not latest_version.version_file:
            return Response(
                data={
                    "version_file": _("The latest version has no file attached to it. Please upload a file first."),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if "metadata" in request.data:
            metadata = request.data.pop("metadata", [])

        # Pre-check if metadata are valid
        if metadata is not None:
            try:
                validate_metadata(metadata)
            except ValidationError as e:
                return Response(
                    data={
                        "metadata": str(e),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        uploads_version = UploadsVersion.objects.create(
            name=serializer.data.get("name", None),
            version_file=latest_version.version_file,
            dataset=dataset,
        )

        if metadata is not None:
            set_metadata_for_relation(
                metadata_list=metadata,
                relation=uploads_version,
            )

        if dataset.is_published() and not uploads_version.is_published():
            uploads_version.publish()

        return Response(
            data=UploadsVersionSerializer(uploads_version).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=inline_serializer(
            name="UploadsDatasetFileActionSerializer",
            fields={
                "file": serializers.FileField(required=True),
            },
        ),
        responses={
            201: UploadsVersionSerializer,
        },
        methods=["POST"],
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="file",
        url_name="file",
        throttle_classes=[],
    )
    def file(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset = self.get_object()
        if dataset.locked and not dataset.is_locked_by_myself():
            return Response(
                data={
                    "lock": _("You must not edit an element which has been locked by another user."),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.data.get("file")
        if not uploaded_file:
            return Response(
                data={
                    "file": _(
                        "You must provide a file to upload.",
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploads_version = create_uploads_version_with_new_file_for_dataset(
            dataset=dataset,
            uploaded_file=uploaded_file,
            original_file_path=request.headers.get("Original-File-Path", None),
        )

        return Response(
            data=UploadsVersionSerializer(uploads_version).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=inline_serializer(
            name="UploadsDatasetRestoreUploadsVersionActionSerializer",
            fields={
                "uploads_version": serializers.UUIDField(required=True),
            },
        ),
        responses={
            201: UploadsVersionSerializer,
        },
        methods=["POST"],
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="restore",
        url_name="restore",
        throttle_classes=[],
    )
    def restore(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dataset = self.get_object()

        try:
            uploads_version = dataset.restore_version(
                uploads_version=request.data.get("uploads_version", None),
            )
        except Exception as e:
            return Response(
                data={
                    "uploads_version": str(e),
                },
                status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDenied) else status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            data=UploadsVersionSerializer(uploads_version).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        description="Create a reference to an existing file on the storage without uploading it.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to an existing file on the storage that should be referenced.",
                    },
                },
                "required": ["filepath"],
            },
        },
        responses={
            200: UploadsDatasetSerializer,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful Reference",
                value={
                    "filepath": "/path/to/existing/file.csv",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Error Response",
                value={
                    "filepath": "No filepath provided.",
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="reference",
        url_name="reference",
        throttle_classes=[],
    )
    def reference(self, request, *args, **kwargs) -> Response:
        """
        Create a reference file for an existing file on the storage.
        This endpoint allows adding files to a dataset by referencing an existing file path.
        """
        dataset = self.get_object()

        # Check if filepath was provided
        filepath = request.data.get("filepath")
        if not filepath:
            return Response(
                {"filepath": _("No filepath provided.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        storage = dataset.folder.storage

        full_filepath = os.path.join(
            settings.PRIVATE_DSS_MOUNT_PATH,
            storage.local_private_dss_path,
            filepath.lstrip("/"),
        )
        logger.info(f"full_filepath: {full_filepath}")

        if not os.path.exists(full_filepath):
            return Response(
                {"filepath": _("File not found at path: {full_filepath}").format(full_filepath=full_filepath)},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Create a new UploadsVersionFile that references the existing file
            with open(full_filepath, "rb"):
                # Directly create and save the UploadsVersionFile instance
                file = UploadsVersionFile.objects.create(
                    uploaded_file=None,
                    status=UploadsVersionFile.Status.SCHEDULED,
                    storage_relocating=UploadsVersionFile.Status.FINISHED,
                    is_referenced=True,
                )

            file.uploaded_file.name = str(full_filepath)
            file.publication_date = timezone.now()
            file.save()

            # Set metadata for the original file path
            set_metadata(
                assigned_to_content_type=file.get_content_type(),
                assigned_to_object_id=file.pk,
                custom_key="ORIGINAL_FILE_PATH",
                value=filepath,
                read_only=True,
            )

            file_name = Path(filepath).name
            set_metadata(
                assigned_to_content_type=file.get_content_type(),
                assigned_to_object_id=file.pk,
                custom_key="ORIGINAL_FILE_NAME",
                value=file_name,
                read_only=True,
            )

            # Create the UploadsVersion with the file reference
            uploads_version = UploadsVersion.objects.create(
                version_file=file,
                dataset=dataset,
            )

            # If the dataset is already published, publish this version too
            if dataset.is_published() and not uploads_version.is_published():
                uploads_version.publish()

            # Try to parse the file type
            try:
                parser = MimeTypeParser(file=uploads_version.version_file)
                parser.parse(set_metadata=True)
            except Exception as e:
                logger.warning(
                    "Retrieving the MIME type for file '{file}' failed: {e}".format(
                        file=uploads_version.version_file,
                        e=e,
                    ),
                )

            # Return the serialized dataset
            serializer = self.get_serializer(uploads_version.dataset)
            return Response(serializer.data)

        except Exception as e:
            return Response(
                {"filepath": _("Failed to create reference file: {e}").format(e=str(e))},
                status=status.HTTP_400_BAD_REQUEST,
            )


def file_iterator(file_path, chunk_size=8192):
    """
    A generator that reads the file in chunks for streaming.
    """
    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            yield chunk


class UploadsVersionViewSet(
    BaseModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    LockStatusMixin,
):
    queryset = UploadsVersion.objects.none()

    serializer_class = UploadsVersionSerializer

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "dataset",
        "version_file",
        "version_file__status",
        "created_by",
        "last_modified_by",
        "dataset__folder",
    ]

    search_fields = [
        "name",
        "version_file__uploaded_file",
    ]

    permission_classes_by_action = {
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "update": [IsAuthenticated],
        "partial_update": [IsAuthenticated],
    }

    def get_permissions(self):
        return [permission() for permission in self.permission_classes_by_action.get(self.action, [])]

    def get_queryset(self):
        """
        Gets the queryset for the view set, with filtering by dataset that respects permissions
        :return: A filtered queryset
        """
        queryset = UploadsVersion.objects.all()

        # Detail view of an uploads version object
        if "pk" in self.kwargs:
            return queryset.my_viewable(view_type="detail")

        # Filter by dataset if provided
        dataset_pk = self.request.query_params.get("dataset", None)
        if dataset_pk:
            # Get the dataset
            try:
                dataset = UploadsDataset.objects.get(id=dataset_pk)
                # Check if user has permission to view this dataset
                user = get_current_user()
                if user.is_authenticated:
                    # Check folder permissions if dataset has a folder
                    if dataset.folder:
                        if can_view_in_folder(user, dataset.folder.pk):
                            return queryset.filter(dataset=dataset_pk).order_by("-creation_date")
                    # If no folder, user must be the creator
                    elif dataset.created_by == user:
                        return queryset.filter(dataset=dataset_pk).order_by("-creation_date")
            except UploadsDataset.DoesNotExist:
                pass

            # Return empty queryset if no permissions or dataset not found
            return queryset.none()

        # Filter by folder if provided
        folder_pk = self.request.query_params.get("dataset__folder", None)
        if folder_pk:
            return queryset.folder_viewable(folder_pk=folder_pk)

        # Return empty queryset if no filters provided
        return queryset.none()

    @extend_schema(
        request=UploadsVersionPayloadSerializer,
        responses={
            200: UploadsVersionSerializer,
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request=UploadsVersionPayloadSerializer,
        responses={
            200: UploadsVersionSerializer,
        },
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    @action(
        detail=True,
        methods=[
            "GET",
            "HEAD",
        ],
        url_path="download",
        url_name="download",
        throttle_classes=[],
    )
    def download(self, request, pk=None):
        """
        Serves a file as a response to GET requests and provides file metadata for HEAD requests.
        """
        instance = self.get_object()
        metadata = instance.version_file.metadata

        file_name = instance.version_file.name
        file_path = os.path.join(instance.version_file.absolute_path, file_name)

        checksum_sha256 = metadata.filter(custom_key="CHECKSUM_SHA256").first()
        original_filename = metadata.filter(custom_key="ORIGINAL_FILE_NAME").first()

        mime_type = metadata.filter(custom_key="MIME_TYPE").first()
        if not mime_type:
            mime_type = MimeTypeParser(instance.version_file).parse()
        else:
            mime_type = mime_type.get_value()

        try:
            # Handle HEAD requests for file metadata
            if request.method == "HEAD":
                # Creates a response with file metadata for HEAD requests, mimicking S3 HEAD responses.
                if not os.path.exists(file_path):
                    return HttpResponseNotFound(_("The requested file does not exist."))

                file_size = os.path.getsize(file_path)
                last_modified_time = os.path.getmtime(file_path)
                last_modified_gmt = format_date_time(last_modified_time)

                response = HttpResponse(status=status.HTTP_200_OK)
                response["File-Size"] = str(file_size)
                response["File-Last-Modified"] = last_modified_gmt
                response["File-Accept-Ranges"] = "bytes"  # Indicates support for range requests. Not yet implemented!
                response["File-Mime-Type"] = mime_type
                response["File-Checksum-SHA256"] = checksum_sha256.get_value() if checksum_sha256 else ""
                response["ETag"] = checksum_sha256.get_value() if checksum_sha256 else ""

                return response

            # Handle GET requests for file download
            if os.path.exists(file_path):
                extension = mimetypes.guess_extension(mime_type)
                suggestion = instance.dataset.name or original_filename.get_value() or file_name

                # This regex operation ensures that:
                # 1. all file extensions get removed, e.g. picture.jpg.jpg
                # 2. all file extensions are found regardless of case, e.g. picture.jpg.Jpg.JPG
                if extension is not None:
                    while re.findall(f"{extension}$", suggestion, flags=re.IGNORECASE):
                        suggestion = re.sub(f"{extension}$", "", suggestion, flags=re.IGNORECASE)

                return FileResponse(
                    open(file_path, "rb"),
                    as_attachment=bool(request.query_params.get("as_attachment")),
                    filename=f"{suggestion}{extension or ''}",
                )
            else:
                return HttpResponseNotFound(_("The requested file does not exist."))
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="compare",
                type=uuid.UUID,
                location=OpenApiParameter.QUERY,
                description="UUID of the UploadsVersion to compare with",
                required=True,
            ),
        ],
        responses={
            200: UploadsVersionDiffResponseSerializer,
        },
    )
    @action(
        detail=True,
        methods=[
            "GET",
        ],
        url_path="diff",
        url_name="diff",
        throttle_classes=[],
    )
    def diff(self, request, *args, **kwargs):
        instance = self.get_object()
        compare = request.query_params.get("compare")

        if not compare:
            return Response(
                data={
                    "compare": _("You must provide an uploads version to compare to."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            compare_uuid = uuid.UUID(compare)
        except ValueError:
            return Response(
                data={
                    "compare": _("Invalid UUID format for compare parameter."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            compare_instance = UploadsVersion.objects.get(pk=compare_uuid)
        except UploadsVersion.DoesNotExist:
            return Response(
                data={
                    "compare": _("An uploads version with this primary key does not exist."),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        older_instance, newer_instance = sorted((instance, compare_instance), key=lambda x: x.creation_date)

        diff = self.compare_instances(newer_instance, older_instance)

        diff["version"] = {
            "old": older_instance,
            "new": newer_instance,
        }

        return Response(
            data=UploadsVersionDiffResponseSerializer(diff).data,
            status=status.HTTP_200_OK,
        )

    def compare_instances(self, newer_instance, older_instance):
        diff = {}

        metadata_diff = self.compare_metadata(newer_instance.metadata.all(), older_instance.metadata.all())
        if metadata_diff:
            diff["metadata"] = metadata_diff

        version_file_diff = self.compare_version_files(newer_instance.version_file, older_instance.version_file)
        if version_file_diff:
            diff["version_file"] = version_file_diff

        return diff

    # TODO: In the future it should be possible to have versions without files. We'll need to change this then.
    def compare_version_files(self, newer_file: UploadsVersionFile, older_file: UploadsVersionFile) -> dict | None:
        if newer_file.pk == older_file.pk:
            return None

        return {
            "old": older_file,
            "new": newer_file,
        }

    def compare_metadata(self, newer_metadata: list[Metadata], older_metadata: list[Metadata]) -> list[dict] | None:
        metadata_diff = []

        newer_dict = {self.get_metadata_key(m): m.get_value() for m in newer_metadata}
        older_dict = {self.get_metadata_key(m): m.get_value() for m in older_metadata}

        all_keys = set(newer_dict.keys()) | set(older_dict.keys())

        for key in all_keys:
            newer_value = newer_dict.get(key)
            older_value = older_dict.get(key)
            if newer_value != older_value:
                metadata_diff.append(
                    {
                        "key": key,
                        "old": older_value,
                        "new": newer_value,
                    },
                )

        return metadata_diff or None

    def get_metadata_key(self, metadata):
        return metadata.field.key if metadata.field else metadata.custom_key


class UploadsVersionFileViewSet(BaseModelViewSet, mixins.RetrieveModelMixin):
    queryset = UploadsVersionFile.objects.none()

    serializer_class = UploadsVersionFileSerializer

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "status",
        "created_by",
        "last_modified_by",
    ]

    search_fields = [
        "uploaded_file",
    ]

    def get_queryset(self):
        """
        Gets the queryset for the view set
        :return:
        """
        return UploadsVersionFile.objects.all()


class TusUploadViewSet(BaseModelViewSet, BaseTusUploadViewSet):
    throttle_classes = []

    filterset_class = []

    filterset_fields = []

    search_fields = []

    pagination_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = None

    def create(self, request, *args, **kwargs):
        try:
            self.dataset = UploadsDataset.objects.get(pk=kwargs.get("dataset_pk", None))
        except UploadsDataset.DoesNotExist:
            return HttpResponse(
                _("A dataset with this primary key does not exist."),
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().create(request, *args, **kwargs)

    def get_success_headers(self, data):
        try:
            url = reverse(
                "uploads-dataset-detail",
                kwargs={
                    "pk": self.dataset.pk,
                },
            )

            return {
                "Location": f"{url}tus/{data['guid']}/",
            }
        except (TypeError, KeyError):
            return {}
