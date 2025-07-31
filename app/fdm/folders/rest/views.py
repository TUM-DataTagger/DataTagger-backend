from django.db.models import Subquery

from rest_framework import filters, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema

from fdm.core.rest.base import BaseModelViewSet
from fdm.core.rest.mixins import *
from fdm.core.rest.permissions import (
    CanCreateFolderPermission,
    CanCreateFolders,
    CanViewFolder,
    IsFolderAdmin,
    IsFolderAdminForPermission,
)
from fdm.folders.helpers import add_folder_permissions_for_users
from fdm.folders.models import *
from fdm.folders.rest.filter import FolderPermissionFilter
from fdm.folders.rest.serializers import *
from fdm.metadata.rest.serializers import MetadataTemplateSerializer

__all__ = [
    "FolderViewSet",
    "FolderPermissionViewSet",
]


class FolderViewSet(
    BaseModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    LockStatusMixin,
    LockMixin,
    UnlockMixin,
):
    queryset = Folder.objects.none()

    serializer_class = FolderSerializer

    serializer_action_classes = {
        "list": FolderListSerializer,
        "create": FolderCreateSerializer,
        "update": FolderUpdateSerializer,
        "partial_update": FolderUpdateSerializer,
    }

    throttle_classes = []

    filterset_class = []

    filterset_fields = [
        "project",
        "metadata_template",
    ]

    search_fields = [
        "name",
    ]

    permission_classes_by_action = {
        "create": [IsAuthenticated, CanCreateFolders],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated, CanViewFolder],
        "update": [IsAuthenticated, IsFolderAdmin],
        "partial_update": [IsAuthenticated, IsFolderAdmin],
        "destroy": [IsAuthenticated, IsFolderAdmin],
        "permissions": [IsAuthenticated, IsFolderAdmin],
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
        return Folder.objects.filter(
            folderpermission__project_membership__member=self.request.user,
        )

    @extend_schema(
        request=FolderCreatePayloadSerializer,
        responses={
            201: FolderSerializer,
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            FolderSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(
        request=FolderUpdatePayloadSerializer,
        responses={
            200: FolderSerializer,
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request=FolderUpdatePayloadSerializer,
        responses={
            200: FolderSerializer,
        },
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter("ordering", exclude=True),
            OpenApiParameter("search", exclude=True),
        ],
        request=FolderPermissionsActionPayloadSerializer,
        responses={
            200: FolderPermissionSerializer(many=True),
        },
        methods=["PUT"],
    )
    @action(
        detail=True,
        methods=["PUT"],
        url_path="permissions",
        url_name="permissions",
        filterset_class=None,
        pagination_class=None,
    )
    def permissions(self, request, *args, **kwargs):
        serializer = FolderPermissionsActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        folder = self.get_object()
        folder_users = request.data.get("folder_users", [])

        add_folder_permissions_for_users(folder, folder_users)

        # Delete folder members which are currently assigned to this folder but are missing from the request
        obsolete_folder_permissions = FolderPermission.objects.filter(
            folder=folder,
        ).exclude(
            project_membership__member__email__in=[user["email"] for user in folder_users],
        )

        for folder_permission in obsolete_folder_permissions:
            folder_permission.delete()

        # Get the updated member list for the response
        folder_permissions = FolderPermission.objects.filter(
            folder=folder,
        ).all()

        return Response(
            data=FolderPermissionSerializer(folder_permissions, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={
            200: MetadataTemplateSerializer(many=True),
        },
        methods=["GET"],
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="metadata-templates",
        url_name="metadata-templates",
        filterset_class=None,
        pagination_class=None,
    )
    def metadata_templates(self, request, *args, **kwargs):
        folder = self.get_object()
        metadata_templates = folder.get_available_metadata_templates()

        return Response(
            data=MetadataTemplateSerializer(metadata_templates, many=True).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    parameters=[
        OpenApiParameter("ordering", exclude=True),
        OpenApiParameter("search", exclude=True),
    ],
)
class FolderPermissionViewSet(
    BaseModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    queryset = FolderPermission.objects.none()

    serializer_class = FolderPermissionSerializer

    serializer_action_classes = {
        "create": FolderPermissionCreateSerializer,
        "update": FolderPermissionUpdateSerializer,
        "partial_update": FolderPermissionUpdateSerializer,
    }

    throttle_classes = []

    filterset_class = FolderPermissionFilter

    filterset_fields = []

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "project_membership__member__email",
    ]

    pagination_class = None

    permission_classes_by_action = {
        "create": [IsAuthenticated, CanCreateFolderPermission],
        "list": [IsAuthenticated, CanViewFolder],
        "retrieve": [IsAuthenticated, CanViewFolder],
        "update": [IsAuthenticated, IsFolderAdminForPermission],
        "partial_update": [IsAuthenticated, IsFolderAdminForPermission],
        "destroy": [IsAuthenticated, IsFolderAdminForPermission],
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
        return FolderPermission.objects.filter(
            folder__pk__in=Subquery(
                FolderPermission.objects.filter(
                    project_membership__member=self.request.user,
                ).values_list(
                    "folder__pk",
                    flat=True,
                ),
            ),
        )

    @extend_schema(
        responses={
            201: FolderPermissionSerializer,
        },
        methods=["POST"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            FolderPermissionSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(
        responses={
            200: FolderPermissionSerializer,
        },
        methods=["PUT"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: FolderPermissionSerializer,
        },
        methods=["PATCH"],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)
