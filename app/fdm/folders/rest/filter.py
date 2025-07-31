from django.db import models
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework
from django_userforeignkey.request import get_current_user

from fdm.folders.models import FolderPermission

__all__ = [
    "FolderPermissionFilter",
]


class FolderPermissionFilter(rest_framework.FilterSet):
    class Member(models.TextChoices):
        ME = "@me", _("Me")

    project_membership__member = rest_framework.Filter(
        label=_("Filter by member"),
        method="filter_by_project_membership_member",
    )

    class Meta:
        model = FolderPermission
        fields = [
            "folder",
            "project_membership__member",
            "project_membership__member__email",
        ]

    def filter_by_project_membership_member(self, queryset, name, value):
        user = get_current_user()

        if not user.is_authenticated:
            return queryset

        if value == self.Member.ME:
            return queryset.filter(project_membership__member=user)
        elif value:
            try:
                value = int(value)
                return queryset.filter(project_membership__member=value)
            except ValueError:
                return queryset.none()

        return queryset
