from django.contrib import admin

from fdm.dbsettings.models import Setting

__all__ = [
    "SettingsAdmin",
]


@admin.register(Setting)
class SettingsAdmin(admin.ModelAdmin):
    list_display = [
        "key",
        "value",
        "description",
        "public",
    ]

    fields = [
        "key",
        "value",
        "description",
        "public",
    ]

    list_filter = [
        "public",
    ]

    search_fields = [
        "key",
        "value",
        "description",
    ]

    readonly_fields = []

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + [
                "key",
                "description",
                "public",
            ]

        return self.readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
