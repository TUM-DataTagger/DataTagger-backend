from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from drf_spectacular.utils import extend_schema_field

from fdm.core.rest.base import BaseModelSerializer
from fdm.core.rest.serializers import (
    BaseModelWithByUserSerializer,
    MetadataContentTypeSerializer,
    MetadataTemplateContentTypePayloadSerializer,
    MetadataTemplateContentTypeSerializer,
)
from fdm.folders.models import Folder
from fdm.metadata.enums import MetadataFieldType
from fdm.metadata.helpers import check_metadata_template_permissions_for_object, get_metadata_value_for_type
from fdm.metadata.models import *
from fdm.projects.models import Project

__all__ = [
    "MetadataFieldSerializer",
    "MetadataConfigFieldSerializer",
    "MetadataSerializer",
    "MinimalMetadataSerializer",
    "MetadataTemplateFieldSerializer",
    "MetadataTemplateFieldNestedSerializer",
    "MetadataTemplateSerializer",
    "MetadataTemplateMinimalSerializer",
    "MetadataTemplateCreateSerializer",
    "MetadataTemplateUpdateSerializer",
    "MetadataPayloadSerializerField",
    "MetadataPayloadSerializer",
]


class MetadataFieldSerializer(BaseModelSerializer):
    class Meta:
        model = MetadataField
        fields = [
            "pk",
            "key",
            "field_type",
            "read_only",
        ]


@extend_schema_field(
    {
        "type": "object",
    },
)
class MetadataConfigFieldSerializer(serializers.Serializer):
    pass


class MetadataSerializer(BaseModelSerializer):
    assigned_to_content_type = MetadataContentTypeSerializer(
        required=False,
        allow_null=True,
    )

    field = MetadataFieldSerializer(
        read_only=True,
    )

    config = MetadataConfigFieldSerializer(
        required=False,
        allow_null=True,
    )

    value = serializers.SerializerMethodField()

    @staticmethod
    def get_value(obj) -> str | dict:
        return get_metadata_value_for_type(obj.field_type, obj.value)

    class Meta:
        model = Metadata
        fields = [
            "pk",
            "field",
            "custom_key",
            "field_type",
            "read_only",
            "value",
            "config",
            "metadata_template_field",
            "assigned_to_content_type",
            "assigned_to_object_id",
        ]


class MinimalMetadataSerializer(BaseModelSerializer):
    field = MetadataFieldSerializer(
        read_only=True,
    )

    value = serializers.SerializerMethodField()

    @staticmethod
    def get_value(obj) -> str | dict:
        return get_metadata_value_for_type(obj.field_type, obj.value)

    class Meta:
        model = Metadata
        fields = [
            "pk",
            "field",
            "custom_key",
            "field_type",
            "read_only",
            "value",
            "config",
            "metadata_template_field",
        ]


class MetadataTemplateFieldSerializer(BaseModelSerializer):
    value = serializers.SerializerMethodField()

    @staticmethod
    def get_value(obj) -> str | dict:
        return get_metadata_value_for_type(obj.field_type, obj.value)

    class Meta:
        model = MetadataTemplateField
        fields = [
            "pk",
            "metadata_template",
            "field",
            "custom_key",
            "field_type",
            "value",
            "config",
            "mandatory",
        ]


class MetadataTemplateFieldNestedSerializer(BaseModelSerializer):
    field = MetadataFieldSerializer(
        required=False,
    )

    value = serializers.SerializerMethodField()

    @staticmethod
    def get_value(obj) -> str | dict:
        return get_metadata_value_for_type(obj.field_type, obj.value)

    class Meta:
        model = MetadataTemplateField
        fields = [
            "pk",
            "field",
            "custom_key",
            "field_type",
            "value",
            "config",
            "mandatory",
        ]


class MetadataTemplateSerializer(BaseModelWithByUserSerializer):
    assigned_to_content_type = MetadataTemplateContentTypeSerializer(
        required=False,
        allow_null=True,
    )

    assigned_to_content_object_name = serializers.SerializerMethodField()

    @staticmethod
    def get_assigned_to_content_object_name(obj) -> str | None:
        if obj.assigned_to_content_object:
            return obj.assigned_to_content_object.name

        return None

    project = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(
        {
            "type": "object",
            "nullable": True,
            "properties": {
                "pk": {
                    "type": "string",
                    "format": "uuid",
                },
                "name": {
                    "type": "string",
                },
            },
        },
    )
    def get_project(obj):
        from django.contrib.contenttypes.models import ContentType

        from fdm.projects.rest.serializers import MinimalProjectSerializer

        if obj.assigned_to_content_type == ContentType.objects.get_for_model(Folder):
            try:
                folder = Folder.objects.get(pk=obj.assigned_to_object_id)
                return MinimalProjectSerializer(folder.project).data
            except Folder.DoesNotExist:
                return None
        elif obj.assigned_to_content_type == ContentType.objects.get_for_model(Project):
            try:
                project = Project.objects.get(pk=obj.assigned_to_object_id)
                return MinimalProjectSerializer(project).data
            except Project.DoesNotExist:
                return None

        return None

    class Meta:
        model = MetadataTemplate
        fields = [
            "pk",
            "name",
            "assigned_to_content_type",
            "assigned_to_object_id",
            "assigned_to_content_object_name",
            "project",
        ]


class MetadataTemplateMinimalSerializer(BaseModelSerializer):
    class Meta:
        model = MetadataTemplate
        fields = [
            "pk",
            "name",
        ]


class MetadataTemplateCreateSerializer(BaseModelSerializer):
    assigned_to_content_type = MetadataTemplateContentTypePayloadSerializer(
        required=False,
        allow_null=True,
    )

    metadata_template_fields = MetadataTemplateFieldNestedSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = MetadataTemplate
        fields = [
            "pk",
            "name",
            "assigned_to_content_type",
            "assigned_to_object_id",
            "metadata_template_fields",
        ]

    def create(self, validated_data):
        assigned_to_content_type = validated_data.get("assigned_to_content_type", None)
        assigned_to_object_id = validated_data.get("assigned_to_object_id", None)
        metadata_template_fields = self.context["request"].data.get("metadata_template_fields", [])
        validated_data.pop("metadata_template_fields", [])

        if bool(assigned_to_content_type) ^ bool(assigned_to_object_id):
            raise ValueError(_("You must either provide a content type and an object id or none of them."))

        check_metadata_template_permissions_for_object(
            content_type=assigned_to_content_type,
            object_id=assigned_to_object_id,
            user=self.context["request"].user,
        )

        metadata_template = MetadataTemplate.objects.create(**validated_data)

        for metadata_template_field in metadata_template_fields:
            value = metadata_template_field.pop("value", None)
            field = MetadataTemplateField.objects.create(
                metadata_template=metadata_template,
                **metadata_template_field,
            )
            field.set_value(value)

        return metadata_template


class MetadataTemplateUpdateSerializer(BaseModelSerializer):
    assigned_to_content_type = MetadataTemplateContentTypePayloadSerializer(
        required=False,
        allow_null=True,
    )

    metadata_template_fields = MetadataTemplateFieldNestedSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = MetadataTemplate
        fields = [
            "pk",
            "name",
            "assigned_to_content_type",
            "assigned_to_object_id",
            "metadata_template_fields",
        ]

    def update(self, instance, validated_data):
        assigned_to_content_type = validated_data.get("assigned_to_content_type", None)
        assigned_to_object_id = validated_data.get("assigned_to_object_id", None)
        metadata_template_fields = self.context["request"].data.get("metadata_template_fields", None)
        validated_data.pop("metadata_template_fields", None)

        if bool(assigned_to_content_type) ^ bool(assigned_to_object_id):
            raise ValueError(_("You must either provide a content type and an object id or none of them."))

        for key, value in validated_data.items():
            setattr(instance, key, value)

        check_metadata_template_permissions_for_object(
            content_type=assigned_to_content_type,
            object_id=assigned_to_object_id,
            user=self.context["request"].user,
        )

        # TODO: Should it be allowed to change the assigned object?
        instance.save()

        if metadata_template_fields is not None:
            MetadataTemplateField.objects.filter(
                metadata_template=instance.pk,
            ).delete()

            for metadata_template_field in metadata_template_fields:
                value = metadata_template_field.pop("value", None)
                field = MetadataTemplateField.objects.create(
                    metadata_template=instance,
                    **metadata_template_field,
                )
                field.set_value(value)

        return instance


@extend_schema_field(
    {
        "type": "object",
        "properties": {
            "field": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                            },
                            "field_type": {
                                "type": "string",
                                "enum": [choice[0] for choice in MetadataFieldType.choices],
                            },
                        },
                        "required": [
                            "key",
                            "field_type",
                        ],
                    },
                    {
                        "type": "string",
                        "nullable": True,
                    },
                ],
            },
            "custom_key": {
                "type": "string",
                "nullable": True,
                "maxLength": Metadata._meta.get_field("custom_key").max_length,
            },
            "field_type": {
                "type": "string",
                "enum": [choice[0] for choice in MetadataFieldType.choices],
            },
            "value": {
                "oneOf": [
                    {
                        "type": "string",
                        "nullable": True,
                    },
                    {
                        "type": "object",
                        "nullable": True,
                    },
                ],
            },
            "config": {
                "type": "object",
                "nullable": True,
            },
            "metadata_template_field": {
                "type": "string",
                "format": "uuid",
                "nullable": True,
            },
        },
    },
)
class MetadataPayloadSerializerField(serializers.Field):
    pass


class MetadataPayloadSerializer(serializers.ListSerializer):
    child = MetadataPayloadSerializerField()
