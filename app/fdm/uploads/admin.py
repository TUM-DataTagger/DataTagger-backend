from django.contrib import admin

from fdm.metadata.filters import IsPublishedFilter
from fdm.uploads.models import UploadsDataset, UploadsVersion, UploadsVersionFile

__all__ = [
    "UploadsVersionInlineAdmin",
    "UploadsDatasetAdmin",
    "UploadsVersionAdmin",
    "UploadsVersionFileAdmin",
]


class UploadsVersionInlineAdmin(admin.TabularInline):
    model = UploadsVersion

    can_delete = False

    show_change_link = False

    fields = [
        "pk",
        "name",
        "version_file",
        "publication_date",
        "is_latest_version",
        "metadata_is_complete",
        "status",
    ]

    readonly_fields = [
        "pk",
        "name",
        "version_file",
        "publication_date",
        "is_latest_version",
        "metadata_is_complete",
        "status",
    ]

    ordering = [
        "-creation_date",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UploadsDataset)
class UploadsDatasetAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "name",
        "folder",
        "is_published",
    ]

    list_filter = [
        "folder__project",
        IsPublishedFilter,
    ]

    search_fields = [
        "pk",
        "name",
        "display_name",
        "folder__pk",
        "folder__name",
        "folder__project__pk",
        "folder__project__name",
    ]

    inlines = [
        UploadsVersionInlineAdmin,
    ]

    readonly_fields = [
        "display_name",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.can_hard_delete_datasets or obj and obj.publication_date is None


@admin.register(UploadsVersion)
class UploadsVersionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "dataset",
        "version_file",
        "is_published",
        "is_latest_version",
    ]

    list_filter = [
        "dataset__folder__project",
        IsPublishedFilter,
    ]

    search_fields = [
        "pk",
        "name",
        "dataset__pk",
        "dataset__name",
        "dataset__display_name",
        "dataset__folder__pk",
        "dataset__folder__name",
        "dataset__folder__project__pk",
        "dataset__folder__project__name",
    ]

    readonly_fields = [
        "metadata_is_complete",
        "status",
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            if not obj.dataset:
                return self.readonly_fields

            if not obj.is_published():
                return self.readonly_fields

            if obj.pk == obj.dataset.latest_version.pk:
                return self.readonly_fields

            return [
                "dataset",
                "version_file",
                "publication_date",
            ] + self.readonly_fields

        return self.readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.can_hard_delete_datasets or obj and obj.publication_date is None


@admin.register(UploadsVersionFile)
class UploadsVersionFileAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "status",
        "uploaded_using_tus",
        "is_published",
        "is_referenced",
    ]

    list_filter = [
        "status",
        "uploaded_using_tus",
        "is_referenced",
        IsPublishedFilter,
    ]

    search_fields = [
        "pk",
        "uploaded_file",
        "uploads_versions__pk",
        "uploads_versions__name",
        "uploads_versions__dataset__pk",
        "uploads_versions__dataset__name",
        "uploads_versions__dataset__display_name",
        "uploads_versions__dataset__folder__pk",
        "uploads_versions__dataset__folder__name",
        "uploads_versions__dataset__folder__project__pk",
        "uploads_versions__dataset__folder__project__name",
    ]

    fields = [
        "name",
        "file_size",
        "absolute_path",
        "status",
        "uploaded_using_tus",
        "is_published",
        "is_referenced",
    ]

    inlines = [
        UploadsVersionInlineAdmin,
    ]

    exclude = [
        "uploaded_file",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.can_hard_delete_datasets or obj and obj.publication_date is None
