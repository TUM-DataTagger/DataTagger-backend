from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from fdm.metadata.models import *

__all__ = [
    "MetadataFieldAdmin",
    "MetadataTemplateAdmin",
    "MetadataTemplateFieldAdmin",
]


@admin.register(MetadataField)
class MetadataFieldAdmin(admin.ModelAdmin):
    list_display = [
        "key",
        "field_type",
        "read_only",
    ]

    list_filter = [
        "field_type",
        "read_only",
    ]

    search_fields = [
        "pk",
        "key",
    ]

    def get_readonly_fields(self, request, obj=None):
        # Make fields readonly for existing entries only which are already in use
        if (
            obj
            and Metadata.objects.filter(field=obj).exists()
            or MetadataTemplateField.objects.filter(field=obj).exists()
        ):
            return list(self.readonly_fields) + [
                "field_type",
            ]

        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        # Fields which are already in use must not be deleted
        if Metadata.objects.filter(field=obj).exists() or MetadataTemplateField.objects.filter(field=obj).exists():
            return False

        return True


@admin.register(MetadataTemplate)
class MetadataTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "get_template_type",
    ]

    list_filter = [
        "assigned_to_content_type",
    ]

    search_fields = [
        "pk",
        "name",
    ]

    def get_template_type(self, obj):
        if bool(obj.assigned_to_content_type) ^ bool(obj.assigned_to_object_id):
            return _("Invalid template type")
        elif obj.assigned_to_content_type and obj.assigned_to_object_id:
            model = obj.assigned_to_content_type.model_class()
            try:
                model_object = model.objects.get(pk=obj.assigned_to_object_id)
            except model.DoesNotExist:
                return _("Invalid template type") + ": " + _("An object type with this object id does not exist.")

            return f"{model.__name__}: {model_object}"
        else:
            return _("Global")

    get_template_type.short_description = _("Template type")


@admin.register(MetadataTemplateField)
class MetadataTemplateFieldAdmin(admin.ModelAdmin):
    list_display = [
        "metadata_template",
        "field",
        "custom_key",
        "value",
        "mandatory",
    ]

    list_filter = [
        "field",
        "mandatory",
    ]

    search_fields = [
        "pk",
        "field__key",
        "custom_key",
        "value",
    ]
