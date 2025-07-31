from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_userforeignkey.request import get_current_user
from drf_spectacular.utils import OpenApiParameter, extend_schema

from fdm.core.helpers import get_content_type_for_model
from fdm.core.rest.base import BaseModelViewSet
from fdm.core.rest.serializers import METADATA_CONTENT_TYPES
from fdm.folders.models import Folder
from fdm.projects.models import Project
from fdm.search.models import ResultsModel
from fdm.search.rest.serializers import SearchSerializer
from fdm.uploads.models import UploadsDataset, UploadsVersion, UploadsVersionFile

__all__ = [
    "SearchViewSet",
]


class SearchViewSet(
    BaseModelViewSet,
    viewsets.ViewSet,
):
    class Settings:
        DEFAULT_LIMIT = 5

        MAX_LIMIT = 20

        ALLOWED_CONTENT_TYPE_MODELS = [
            Project,
            Folder,
            UploadsDataset,
            UploadsVersion,
            UploadsVersionFile,
        ]

    serializer_class = SearchSerializer

    throttle_classes = []

    filterset_class = []

    filterset_fields = []

    search_fields = []

    permission_classes_by_action = {
        "search_global": [IsAuthenticated],
    }

    def get_permissions(self):
        return [permission() for permission in self.permission_classes_by_action.get(self.action, [])]

    def get_limit(self, user_limit: str) -> int:
        try:
            limit = int(user_limit)

            if not self.Settings.MAX_LIMIT >= limit > 0:
                limit = self.Settings.DEFAULT_LIMIT
        except (TypeError, ValueError):
            limit = self.Settings.DEFAULT_LIMIT

        return limit

    def get_allowed_content_types(self) -> list[str]:
        from django.contrib.contenttypes.models import ContentType

        return [
            "{0.app_label}.{0.model}".format(
                ContentType.objects.get_for_model(content_type_model),
            )
            for content_type_model in self.Settings.ALLOWED_CONTENT_TYPE_MODELS
        ]

    def get_validated_content_types(self, content_types: str) -> list[str] | bool:
        try:
            content_types = content_types.split(",")

            for content_type in content_types:
                if content_type not in self.get_allowed_content_types():
                    return False

            return content_types

        except (TypeError, ValueError):
            return False

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "content_types",
                type=str,
                many=True,
                style="form",
                explode=False,
                enum=METADATA_CONTENT_TYPES,
            ),
            OpenApiParameter("term", str),
            OpenApiParameter("limit", int),
        ],
        responses={
            200: SearchSerializer,
        },
        methods=["GET"],
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="global",
        url_name="global",
        filterset_class=None,
        pagination_class=None,
    )
    def search_global(self, request):
        current_user = get_current_user()
        content_types_parameter = request.query_params.get("content_types", None)
        search_term = request.query_params.get("term", None)
        limit = self.get_limit(request.query_params.get("limit"))

        if not search_term:
            return Response(
                data={
                    "term": _("Term parameter is required."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if content_types_parameter is not None:
            content_types = self.get_validated_content_types(content_types_parameter)

            if not content_types:
                return Response(
                    data={
                        "content_types": _("Content types parameter contains illegal values."),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            content_types = self.get_allowed_content_types()

        results = ResultsModel()

        # Search for projects
        # Finds: projects, folders
        setattr(results, "projects", [])
        if get_content_type_for_model(Project) in content_types:
            results.projects = (
                Project.objects.filter(
                    # Only projects with an upright membership
                    project_members__member=current_user if current_user.pk else None,
                )
                .filter(
                    # Project fields
                    Q(name__icontains=search_term)
                    | Q(description__icontains=search_term)
                    | Q(metadata__custom_key__icontains=search_term)
                    | Q(metadata__value__icontains=search_term)
                    # Folder fields
                    | Q(folder__name__icontains=search_term)
                    | Q(folder__description__icontains=search_term)
                    | Q(folder__metadata__custom_key__icontains=search_term)
                    | Q(folder__metadata__value__icontains=search_term),
                )
                .distinct()[:limit]
            )

        # Search for folders
        # Finds: folders
        setattr(results, "folders", [])
        if get_content_type_for_model(Folder) in content_types:
            results.folders = (
                Folder.objects.filter(
                    # Only folders with an upright folder permission
                    folderpermission__project_membership__member=current_user if current_user.pk else None,
                )
                .filter(
                    # Folder fields
                    Q(name__icontains=search_term)
                    | Q(description__icontains=search_term)
                    | Q(metadata__custom_key__icontains=search_term)
                    | Q(metadata__value__icontains=search_term)
                    # Dataset fields
                    | Q(uploads_dataset__name__icontains=search_term)
                    # Version fields
                    | Q(uploads_dataset__uploads_versions__name__icontains=search_term)
                    | Q(uploads_dataset__uploads_versions__metadata__custom_key__icontains=search_term)
                    | Q(uploads_dataset__uploads_versions__metadata__value__icontains=search_term)
                    # Version file fields
                    | Q(uploads_dataset__uploads_versions__version_file__metadata__custom_key__icontains=search_term)
                    | Q(uploads_dataset__uploads_versions__version_file__metadata__value__icontains=search_term),
                )
                .distinct()[:limit]
            )

        # Search for datasets
        # Finds: datasets, versions, version files
        setattr(results, "uploads_datasets", [])
        if get_content_type_for_model(UploadsDataset) in content_types:
            results.uploads_datasets = (
                UploadsDataset.objects.all_viewable(
                    # Only datasets in folders with an upright folder permission or in the drafts section
                )
                .filter(
                    # Dataset fields
                    Q(name__icontains=search_term)
                    # Version fields
                    | Q(uploads_versions__name__icontains=search_term)
                    | Q(uploads_versions__metadata__custom_key__icontains=search_term)
                    | Q(uploads_versions__metadata__value__icontains=search_term)
                    # Version file fields
                    | Q(uploads_versions__version_file__metadata__custom_key__icontains=search_term)
                    | Q(uploads_versions__version_file__metadata__value__icontains=search_term),
                )
                .distinct()[:limit]
            )

        # Search for versions
        # Finds: versions, version files
        setattr(results, "uploads_versions", [])
        if get_content_type_for_model(UploadsVersion) in content_types:
            results.uploads_versions = (
                UploadsVersion.objects.filter(
                    # Only versions part of datasets which are in folders with an upright folder permission
                    # or in the drafts section
                    dataset__in=UploadsDataset.objects.all_viewable().values("pk"),
                )
                .filter(
                    # Version fields
                    Q(name__icontains=search_term)
                    | Q(metadata__custom_key__icontains=search_term)
                    | Q(metadata__value__icontains=search_term)
                    # Version file fields
                    | Q(version_file__metadata__custom_key__icontains=search_term)
                    | Q(version_file__metadata__value__icontains=search_term),
                )
                .distinct()[:limit]
            )

        return Response(
            data=SearchSerializer(results).data,
            status=status.HTTP_200_OK,
        )
