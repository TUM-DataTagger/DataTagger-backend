from django.db.models import Subquery
from django.utils.translation import gettext_lazy as _

from rest_framework import filters, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema

from fdm.core.helpers import get_or_create_user
from fdm.core.rest.base import BaseModelViewSet
from fdm.core.rest.mixins import *
from fdm.core.rest.permissions import (
    CanCreateProject,
    CanCreateProjectMembership,
    CanDeleteProjectMembership,
    IsProjectAdmin,
    IsProjectAdminForMembership,
    IsProjectMember,
    IsProjectMemberForMembership,
)
from fdm.folders.models import Folder
from fdm.folders.rest.serializers import FolderListSerializer
from fdm.metadata.rest.serializers import MetadataTemplateSerializer
from fdm.projects.models import *
from fdm.projects.rest.filter import ProjectCreatorFilter, ProjectMembershipFilter
from fdm.projects.rest.serializers import *

__all__ = [
    "ProjectViewSet",
    "ProjectMembershipViewSet",
]


class ProjectViewSet(
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
    queryset = Project.objects.none()

    serializer_class = ProjectSerializer

    serializer_action_classes = {
        "list": ProjectListSerializer,
        "create": ProjectCreateSerializer,
        "update": ProjectUpdateSerializer,
        "partial_update": ProjectUpdateSerializer,
    }

    throttle_classes = []

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = ProjectCreatorFilter

    filterset_fields = []

    search_fields = [
        "name",
    ]

    ordering_fields = [
        "name",
        "creation_date",
    ]

    permission_classes_by_action = {
        "create": [IsAuthenticated, CanCreateProject],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated, IsProjectMember],
        "update": [IsAuthenticated, IsProjectAdmin],
        "partial_update": [IsAuthenticated, IsProjectAdmin],
        "destroy": [IsAuthenticated, IsProjectAdmin],
        "members": [IsAuthenticated, IsProjectAdmin],
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
        return Project.objects.filter(
            project_members__member=self.request.user,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
            OpenApiParameter("is_deletable", bool),
            OpenApiParameter(
                name="created_by",
                type=str,
                enum=[
                    "me",
                    "others",
                ],
                default="",
                required=False,
            ),
            OpenApiParameter(
                name="membership",
                type=str,
                enum=[
                    "admin",
                    "member",
                ],
                default="",
                required=False,
            ),
        ],
        responses={
            200: ProjectSerializer(many=True),
        },
        methods=["GET"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request=ProjectCreatePayloadSerializer,
        responses={
            201: ProjectSerializer,
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            ProjectSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(
        request=ProjectUpdatePayloadSerializer,
        responses={
            200: ProjectSerializer,
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request=ProjectUpdatePayloadSerializer,
        responses={
            200: ProjectSerializer,
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
        request=ProjectMembersActionPayloadSerializer,
        responses={
            200: ProjectMembershipSerializer(many=True),
        },
        methods=["PUT"],
    )
    @action(
        detail=True,
        methods=["PUT"],
        url_path="members",
        url_name="members",
        filterset_class=None,
        pagination_class=None,
    )
    def members(self, request, *args, **kwargs):
        serializer = ProjectMembersActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = self.get_object()
        project_users = request.data.get("project_users", [])

        # Update the permissions of existing project members or create a new project member
        for user in project_users:
            try:
                project_membership = ProjectMembership.objects.get(
                    project=project,
                    member__email=user["email"],
                )
                project_membership.is_project_admin = user["is_project_admin"]
                project_membership.can_create_folders = user["can_create_folders"]
                project_membership.is_metadata_template_admin = user["is_metadata_template_admin"]
                project_membership.save()
            except ProjectMembership.DoesNotExist:
                ProjectMembership.objects.create(
                    project=project,
                    member=get_or_create_user(user["email"]),
                    is_project_admin=user["is_project_admin"],
                    can_create_folders=user["can_create_folders"],
                    is_metadata_template_admin=user["is_metadata_template_admin"],
                )

        # Delete project members which are currently assigned to this project but are missing from the request
        obsolete_project_memberships = ProjectMembership.objects.filter(
            project=project,
        ).exclude(
            member__email__in=[user["email"] for user in project_users],
        )

        for project_membership in obsolete_project_memberships:
            project_membership.delete()

        # Get the updated member list for the response
        project_members = ProjectMembership.objects.filter(
            project=project,
        ).all()

        return Response(
            data=ProjectMembershipSerializer(project_members, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description=_("List folders assigned to a project."),
        responses={
            200: FolderListSerializer(many=True),
        },
        methods=["GET"],
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="folders",
        url_name="folders",
        filterset_class=None,
        pagination_class=None,
    )
    def folders(self, request, *args, **kwargs):
        project = self.get_object()

        folders = Folder.objects.filter(
            project=project,
            folderpermission__project_membership__member=self.request.user,
        ).order_by("name")

        return Response(
            data=FolderListSerializer(folders, many=True).data,
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
        project = self.get_object()
        metadata_templates = project.get_available_metadata_templates()

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
class ProjectMembershipViewSet(
    BaseModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    queryset = ProjectMembership.objects.none()

    serializer_class = ProjectMembershipSerializer

    serializer_action_classes = {
        "create": ProjectMembershipCreateSerializer,
        "update": ProjectMembershipUpdateSerializer,
        "partial_update": ProjectMembershipUpdateSerializer,
    }

    throttle_classes = []

    filterset_class = ProjectMembershipFilter

    filterset_fields = []

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "member__email",
    ]

    ordering_fields = [
        "pk",
        "project",
        "member",
        "member__email",
        "is_project_admin",
        "can_create_folders",
    ]

    pagination_class = None

    permission_classes_by_action = {
        "create": [IsAuthenticated, CanCreateProjectMembership],
        "list": [IsAuthenticated],
        "retrieve": [IsAuthenticated, IsProjectMemberForMembership],
        "update": [IsAuthenticated, IsProjectAdminForMembership],
        "partial_update": [IsAuthenticated, IsProjectAdminForMembership],
        "destroy": [IsAuthenticated, CanDeleteProjectMembership],
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
        return ProjectMembership.objects.filter(
            project__pk__in=Subquery(
                ProjectMembership.objects.filter(
                    member=self.request.user,
                ).values_list(
                    "project__pk",
                    flat=True,
                ),
            ),
        )

    @extend_schema(
        responses={
            201: ProjectMembershipSerializer,
        },
        methods=["POST"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            ProjectMembershipSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(
        responses={
            200: ProjectMembershipSerializer,
        },
        methods=["PUT"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: ProjectMembershipSerializer,
        },
        methods=["PATCH"],
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)
