import logging
import uuid

from django.core.exceptions import ValidationError
from django.db.models import Q, Subquery
from django.utils.translation import gettext_lazy as _

from rest_framework import filters, mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_userforeignkey.request import get_current_user
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from waffle.mixins import WaffleSwitchMixin

from fdm.core.helpers import get_content_type_for_model, get_content_type_instance
from fdm.core.rest.base import BaseModelViewSet
from fdm.core.rest.mixins import LockMixin, LockStatusMixin, UnlockMixin
from fdm.core.rest.permissions import (
    CanEditMetadataTemplate,
    can_edit_in_folder,
    is_folder_metadata_template_admin,
    is_project_metadata_template_admin,
)
from fdm.core.rest.serializers import METADATA_CONTENT_TYPES, METADATA_TEMPLATE_CONTENT_TYPES
from fdm.metadata.helpers import validate_metadata
from fdm.metadata.models import *
from fdm.metadata.rest.filter import ContentTypeFilter
from fdm.metadata.rest.serializers import *
from fdm.uploads.helpers import create_uploads_version_with_new_metadata_for_dataset
from fdm.uploads.models import UploadsDataset

__all__ = [
    "MetadataFieldViewSet",
    "MetadataViewSet",
    "MetadataTemplateViewSet",
    "MetadataTemplateFieldViewSet",
]

logger = logging.getLogger(__name__)


class MetadataFieldViewSet(WaffleSwitchMixin, BaseModelViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    waffle_switch = "metadata_field_switch"

    queryset = MetadataField.objects.none()

    serializer_class = MetadataFieldSerializer

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "field_type",
        "read_only",
    ]

    search_fields = [
        "key",
    ]

    def get_queryset(self):
        """
        Gets the queryset for the view set
        :return:
        """
        return MetadataField.objects.all()


class MetadataViewSet(
    BaseModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    queryset = Metadata.objects.none()

    serializer_class = MetadataSerializer

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "assigned_to_content_type",
        "assigned_to_object_id",
    ]

    filter_backends = [
        ContentTypeFilter,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = []

    pagination_class = None

    def get_queryset(self):
        """
        Gets the queryset for the view set
        :return:
        """
        return Metadata.objects.all()

    @extend_schema(
        parameters=[
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
            OpenApiParameter(
                name="assigned_to_content_type",
                type=str,
                enum=METADATA_CONTENT_TYPES,
                default="",
                required=False,
            ),
            OpenApiParameter("assigned_to_object_id", uuid.UUID),
        ],
        responses={
            200: MetadataSerializer(many=True),
        },
        methods=["GET"],
    )
    def list(self, request, *args, **kwargs):
        assigned_to_content_type = request.query_params.get("assigned_to_content_type", None)
        assigned_to_object_id = request.query_params.get("assigned_to_object_id", None)

        # Prevent this non-paginated list endpoint from returning every metadata entry without filtering it
        if not assigned_to_content_type and not assigned_to_object_id:
            return Response(
                MetadataSerializer([], many=True).data,
                status=status.HTTP_200_OK,
            )

        return super().list(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter("ordering", exclude=True),
            OpenApiParameter("search", exclude=True),
        ],
        request=inline_serializer(
            name="MetadataBulkActionSerializer",
            fields={
                "metadata": MetadataPayloadSerializer(
                    required=True,
                ),
                "uploads_datasets": serializers.ListSerializer(
                    child=serializers.UUIDField(),
                    required=True,
                ),
            },
        ),
        description=_("Adds metadata for multiple uploads datasets in bulk."),
        responses={
            201: None,
        },
        methods=["POST"],
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="bulk-add-to-uploads-datasets",
        url_name="bulk-add-to-uploads-datasets",
        filterset_class=None,
        pagination_class=None,
    )
    def metadata(self, request, *args, **kwargs):
        # Get all uploads datasets the metadata should be added to
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

        if any([not dataset.is_published() and dataset.created_by != request.user for dataset in uploads_datasets]):
            return Response(
                data={
                    "uploads_datasets": _(
                        "You must not edit any unpublished uploads datasets you haven't created yourself.",
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if any(
            [
                dataset.is_published()
                and not can_edit_in_folder(
                    user=request.user,
                    folder_pk=dataset.folder.pk,
                )
                for dataset in uploads_datasets
            ],
        ):
            return Response(
                data={
                    "uploads_datasets": _(
                        "You must not edit any published uploads datasets in a folder you haven't got the permission to.",
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        metadata_list = request.data.get("metadata", [])
        if not len(metadata_list):
            return Response(
                data={
                    "metadata": _("You must provide at least one metadata."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Pre-check if metadata are valid
        try:
            validate_metadata(metadata_list)
        except ValidationError as e:
            return Response(
                data={
                    "metadata": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        for dataset in uploads_datasets:
            try:
                create_uploads_version_with_new_metadata_for_dataset(
                    dataset=dataset,
                    metadata_list=metadata_list,
                    retain_existing_metadata=True,
                )
            except Exception as e:
                logger.error(f"Could not apply new metadata to uploads dataset {dataset}: {e}")

        return Response(
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="assigned_to_content_type",
            type=str,
            enum=METADATA_TEMPLATE_CONTENT_TYPES,
            default="",
            required=False,
        ),
    ],
)
class MetadataTemplateViewSet(
    WaffleSwitchMixin,
    BaseModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    LockStatusMixin,
    LockMixin,
    UnlockMixin,
):
    waffle_switch = "metadata_template_switch"

    queryset = MetadataTemplate.objects.none()

    serializer_class = MetadataTemplateSerializer

    serializer_action_classes = {
        "create": MetadataTemplateCreateSerializer,
        "update": MetadataTemplateUpdateSerializer,
        "partial_update": MetadataTemplateUpdateSerializer,
    }

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "assigned_to_content_type",
        "assigned_to_object_id",
    ]

    filter_backends = [
        ContentTypeFilter,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "name",
    ]

    permission_classes_by_action = {
        "create": [IsAuthenticated],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated],
        "update": [IsAuthenticated, CanEditMetadataTemplate],
        "partial_update": [IsAuthenticated, CanEditMetadataTemplate],
    }

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()

    def get_permissions(self):
        return [permission() for permission in self.permission_classes_by_action.get(self.action, [])]

    @extend_schema(
        parameters=[
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
            OpenApiParameter(
                name="assigned_to_content_type",
                type=str,
                enum=METADATA_CONTENT_TYPES,
                default="",
                required=False,
            ),
            OpenApiParameter("assigned_to_object_id", uuid.UUID),
        ],
        responses={
            200: MetadataTemplateSerializer(many=True),
        },
        methods=["GET"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """
        Gets the queryset for the view set
        :return:
        """
        from django.contrib.contenttypes.models import ContentType

        from fdm.folders.models import Folder, FolderPermission
        from fdm.projects.models import Project, ProjectMembership

        user = get_current_user()

        # Global metadata templates
        query = Q(
            assigned_to_content_type__isnull=True,
            assigned_to_object_id__isnull=True,
        )

        if user.is_authenticated:
            # Project metadata templates
            query |= Q(
                assigned_to_content_type=ContentType.objects.get_for_model(Project),
                assigned_to_object_id__in=Subquery(
                    ProjectMembership.objects.filter(
                        member=self.request.user,
                    ).values_list(
                        "project__pk",
                        flat=True,
                    ),
                ),
            )

            # Folder metadata templates
            query |= Q(
                assigned_to_content_type=ContentType.objects.get_for_model(Folder),
                assigned_to_object_id__in=Subquery(
                    FolderPermission.objects.filter(
                        project_membership__member=self.request.user,
                    ).values_list(
                        "folder__pk",
                        flat=True,
                    ),
                ),
            )

            return MetadataTemplate.objects.filter(query).distinct()

        return MetadataTemplate.objects.none()

    @extend_schema(
        responses={
            201: MetadataTemplateSerializer,
        },
        methods=["POST"],
    )
    def create(self, request, *args, **kwargs):
        from fdm.folders.models import Folder
        from fdm.projects.models import Project

        metadata_template_fields = None

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Permission check for global metadata templates
        if not request.data.get("assigned_to_content_type") and not request.data.get("assigned_to_object_id"):
            if not request.user.is_global_metadata_template_admin:
                return Response(
                    data={
                        "assigned_to_object_id": _(
                            "You do not have permission to create global metadata templates.",
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Permission check for linked metadata template type
        else:
            content_type_instance = get_content_type_instance(request.data.get("assigned_to_content_type"))
            model_class = content_type_instance.model_class()

            if get_content_type_for_model(model_class) == get_content_type_for_model(Project):
                if not is_project_metadata_template_admin(request.user, request.data.get("assigned_to_object_id")):
                    return Response(
                        data={
                            "assigned_to_object_id": _(
                                "You do not have permission to create a metadata template for this project.",
                            ),
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            elif get_content_type_for_model(model_class) == get_content_type_for_model(Folder):
                if not is_folder_metadata_template_admin(request.user, request.data.get("assigned_to_object_id")):
                    return Response(
                        data={
                            "assigned_to_object_id": _(
                                "You do not have permission to create a metadata template for this folder.",
                            ),
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        if "metadata_template_fields" in request.data:
            metadata_template_fields = request.data.get("metadata_template_fields", [])

        # Pre-check if metadata fields are valid
        if metadata_template_fields is not None:
            try:
                validate_metadata(metadata_template_fields)
            except ValidationError as e:
                return Response(
                    data={
                        "metadata_template_fields": str(e),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            MetadataTemplateSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(
        responses={
            200: MetadataTemplateSerializer,
        },
        methods=["PUT"],
    )
    def update(self, request, *args, **kwargs):
        from fdm.folders.models import Folder
        from fdm.projects.models import Project

        instance = self.get_object()

        # TODO: This should not be possible when metadata templates will have versions in the future
        metadata_template_fields = None

        # Permission check for global metadata templates
        if not instance.assigned_to_content_type and not instance.assigned_to_object_id:
            if not request.user.is_global_metadata_template_admin:
                return Response(
                    data={
                        "assigned_to_object_id": _(
                            "You do not have permission to edit global metadata templates.",
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Permission check for linked metadata template type
        else:
            content_type_instance = get_content_type_instance(instance.assigned_to_content_type)
            model_class = content_type_instance.model_class()

            if (
                get_content_type_for_model(model_class) == get_content_type_for_model(Project)
                and not is_project_metadata_template_admin(request.user, instance.assigned_to_object_id)
                or get_content_type_for_model(model_class) == get_content_type_for_model(Folder)
                and not is_folder_metadata_template_admin(request.user, instance.assigned_to_object_id)
            ):
                return Response(
                    data={
                        "assigned_to_object_id": _(
                            "You do not have permission to edit this metadata template.",
                        ),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        if "metadata_template_fields" in request.data:
            metadata_template_fields = request.data.get("metadata_template_fields", [])

        # Pre-check if metadata fields are valid
        if metadata_template_fields is not None:
            try:
                validate_metadata(metadata_template_fields)
            except ValidationError as e:
                return Response(
                    data={
                        "metadata_template_fields": str(e),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: MetadataTemplateSerializer,
        },
        methods=["PATCH"],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class MetadataTemplateFieldViewSet(
    WaffleSwitchMixin,
    BaseModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    waffle_switch = "metadata_template_field_switch"

    queryset = MetadataTemplateField.objects.none()

    serializer_class = MetadataTemplateFieldSerializer

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "metadata_template",
        "field",
    ]

    search_fields = [
        "custom_key",
    ]

    def get_queryset(self):
        """
        Gets the queryset for the view set
        :return:
        """
        return MetadataTemplateField.objects.all()
