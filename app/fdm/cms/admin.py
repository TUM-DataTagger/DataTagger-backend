from django.contrib import admin
from django.db import models

from martor.widgets import AdminMartorWidget

from fdm.cms.models.models import Content


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    actions = []  # Removes the delete action
    add_permissions = []  # Removes the ability to add new entries
    delete_permissions = []  # Removes the ability to delete entries

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Media:
        css = {
            "all": ("cms/admin/custom.css",),
        }

    def get_readonly_fields(self, request, obj=None):
        # Make fields readonly for existing entries only
        if obj:
            return list(self.readonly_fields) + [
                "slug",
                "name",
            ]

        return self.readonly_fields

    def get_prepopulated_fields(self, request, obj=None):
        # Prepopulation works for new objects only
        if not obj:
            return {"slug": ("name",)}

        return {}

    formfield_overrides = {
        models.TextField: {
            "widget": AdminMartorWidget,
        },
    }

    fields = (
        "name",
        "slug",
        "published",
        "text_de",
        "text_en",
    )
    list_display = (
        "name",
        "slug",
        "published",
        "last_modified_by",
        "last_modification_date",
    )
    search_fields = (
        "name",
        "text_de",
        "text_en",
        "slug",
    )
