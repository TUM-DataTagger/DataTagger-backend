from django.contrib import admin

from fdm.folders.models import Folder, FolderPermission

__all__ = [
    "FolderAdmin",
    "FolderPermissionAdmin",
]


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "project",
        "storage",
        "created_by",
        "datasets_count",
        "members_count",
        "metadata_templates_count",
    ]

    list_filter = [
        "project",
        "storage",
        "created_by",
    ]

    search_fields = [
        "pk",
        "name",
        "project__pk",
        "project__name",
        "storage__pk",
        "storage__name",
    ]

    exclude = [
        "description",
    ]

    readonly_fields = [
        "datasets_count",
        "members_count",
        "metadata_templates_count",
    ]


@admin.register(FolderPermission)
class FolderPermissionAdmin(admin.ModelAdmin):
    list_display = [
        "project_membership",
        "folder",
        "is_folder_admin",
        "can_edit",
    ]

    list_filter = [
        "project_membership__project",
        "project_membership__member",
        "is_folder_admin",
        "can_edit",
    ]

    search_fields = [
        "pk",
        "project_membership__project__pk",
        "project_membership__project__name",
        "project_membership__member__pk",
        "folder__pk",
        "folder__name",
    ]
