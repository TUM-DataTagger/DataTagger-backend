import re
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext_lazy as _

from fdm.core.helpers import check_empty_value, get_content_type_for_model, get_content_type_for_object
from fdm.core.rest.permissions import is_folder_metadata_template_admin, is_project_metadata_template_admin
from fdm.folders.models import Folder
from fdm.metadata.enums import MetadataFieldType
from fdm.metadata.models import Metadata, MetadataField, MetadataTemplate, MetadataTemplateField
from fdm.projects.models import Project

__all__ = [
    "get_metadata_structure_for_type",
    "get_metadata_value_for_type",
    "set_metadata",
    "validate_metadata",
    "delete_metadata_for_relation",
    "set_metadata_for_relation",
    "check_metadata_template_permissions_for_object",
    "create_metadata_template_for_object",
    "validate_metadata_integer",
    "validate_metadata_decimal",
    "validate_metadata_datetime_format",
    "validate_metadata_datetime",
    "validate_metadata_date",
    "validate_metadata_time",
    "validate_metadata_selection",
    "validate_metadata_wysiwyg",
    "validate_metadata_value",
]


def get_metadata_structure_for_type(field_type, value):
    value = check_empty_value(value)

    if field_type in [
        MetadataFieldType.INTEGER,
        MetadataFieldType.DECIMAL,
        MetadataFieldType.DATETIME,
        MetadataFieldType.DATE,
        MetadataFieldType.TIME,
        MetadataFieldType.TEXT,
        MetadataFieldType.SELECTION,
    ]:
        return dict(
            value=str(value) if value is not None else None,
        )
    elif field_type == MetadataFieldType.WYSIWYG:
        return dict() if value is None else value

    return value


def get_metadata_value_for_type(field_type, value):
    if value is None:
        return None

    if field_type in [
        MetadataFieldType.INTEGER,
        MetadataFieldType.DECIMAL,
        MetadataFieldType.DATETIME,
        MetadataFieldType.DATE,
        MetadataFieldType.TIME,
        MetadataFieldType.TEXT,
        MetadataFieldType.SELECTION,
    ]:
        return value.get("value")
    elif field_type == MetadataFieldType.WYSIWYG:
        return value

    return value


def set_metadata(
    custom_key=None,
    value=None,
    config=None,
    metadata_template_field=None,
    field_type=None,
    field=None,
    read_only=False,
    assigned_to_content_type=None,
    assigned_to_object_id=None,
):
    if field and custom_key:
        raise ValidationError(_("You must not link a metadata field and declare a custom key together."))

    if not field and not custom_key:
        raise ValidationError(_("You must either link a metadata field or declare a custom key."))

    value = check_empty_value(value)

    field_type = field_type if field_type else field.field_type if field else None or MetadataFieldType.TEXT

    if isinstance(metadata_template_field, str):
        try:
            metadata_template_field = MetadataTemplateField.objects.get(pk=metadata_template_field)
        except MetadataTemplateField.DoesNotExist:
            raise ValidationError(_("The metadata template field does not exist."))

    return Metadata.objects.create(
        assigned_to_content_type=assigned_to_content_type,
        assigned_to_object_id=assigned_to_object_id,
        field_id=field.pk if isinstance(field, MetadataField) else field,
        custom_key=custom_key,
        field_type=field_type,
        value=get_metadata_structure_for_type(
            field_type=field_type,
            value=value,
        ),
        config=config or {},
        metadata_template_field=metadata_template_field,
        read_only=read_only,
    )


def validate_metadata(
    metadata_list: list[dict | Metadata | MetadataTemplateField],
) -> None:
    for metadata in metadata_list:
        if isinstance(metadata, Metadata) or isinstance(metadata, MetadataTemplateField):
            field = metadata.field
            custom_key = metadata.custom_key
            field_type = metadata.field_type
            value = metadata.get_value()
            config = metadata.config
        else:
            field = metadata.get("field", None)
            custom_key = metadata.get("custom_key", None)
            field_type = metadata.get("field_type", None)
            value = metadata.get("value", None)
            config = metadata.get("config", {})

        if isinstance(field, dict):
            try:
                field = MetadataField.objects.get(key=field["key"])
                field_type = field.field_type
                custom_key = field.key
            except MetadataField.DoesNotExist:
                custom_key = field["key"]
                field_type = field["field_type"]
        elif isinstance(field, str):
            try:
                field = MetadataField.objects.get(pk=field)
                field_type = field.field_type
                custom_key = field.key
            except MetadataField.DoesNotExist:
                field_type = None
                custom_key = field

        value = check_empty_value(value)

        if isinstance(metadata, MetadataTemplateField):
            ValidationModel = MetadataTemplateField
        else:
            ValidationModel = Metadata

        ValidationModel(
            custom_key=custom_key,
            field_type=field_type,
            value=get_metadata_structure_for_type(
                field_type=field_type,
                value=value,
            ),
            config=config or {},
        ).clean()


def delete_metadata_for_relation(relation: any) -> None:
    Metadata.objects.filter(
        assigned_to_content_type=relation.get_content_type(),
        assigned_to_object_id=relation.pk,
    ).delete()


def set_metadata_for_relation(
    metadata_list: list[dict | Metadata | MetadataTemplateField],
    relation: any,
    retain_existing_metadata: bool = False,
) -> None:
    if not retain_existing_metadata:
        delete_metadata_for_relation(relation=relation)

    for metadata in metadata_list:
        # A metadata field can either be an existing pk or an object to create a new metadata field on the fly
        if isinstance(metadata, Metadata) or isinstance(metadata, MetadataTemplateField):
            field = metadata.field
            custom_key = metadata.custom_key
            field_type = metadata.field_type
            value = metadata.get_value()
            config = metadata.config

            if isinstance(metadata, Metadata):
                metadata_template_field = metadata.metadata_template_field
            elif isinstance(metadata, MetadataTemplateField):
                metadata_template_field = metadata
            else:
                metadata_template_field = None
        else:
            field = metadata.get("field", None)
            custom_key = metadata.get("custom_key", None)
            field_type = metadata.get("field_type", None)
            value = metadata.get("value", None)
            config = metadata.get("config", {})
            metadata_template_field = metadata.get("metadata_template_field", None)

        if isinstance(field, dict):
            try:
                field = MetadataField.objects.create(
                    key=field["key"],
                    field_type=field["field_type"],
                )
            except ValidationError:
                field = MetadataField.objects.get(key=field["key"])

            field_type = field.field_type

        value = check_empty_value(value)

        set_metadata(
            field=field.pk if isinstance(field, MetadataField) else field,
            field_type=field_type or MetadataFieldType.TEXT,
            custom_key=custom_key,
            value=value,
            config=config,
            metadata_template_field=metadata_template_field,
            assigned_to_content_type=relation.get_content_type(),
            assigned_to_object_id=relation.pk,
        )


def check_metadata_template_permissions_for_object(
    content_type=None,
    object_id=None,
    user=None,
):
    if user is None:
        return

    # Permission check for global metadata templates
    if not content_type and not object_id and not user.is_global_metadata_template_admin:
        raise PermissionDenied

    # Permission check for linked metadata template type
    if content_type == get_content_type_for_model(Project) and not is_project_metadata_template_admin(user, object_id):
        raise PermissionDenied
    elif content_type == get_content_type_for_model(Folder) and not is_folder_metadata_template_admin(user, object_id):
        raise PermissionDenied


def create_metadata_template_for_object(
    metadata_template_data: any,
    metadata_template_fields: list,
    assigned_to_object: any = None,
    user: any = None,
) -> MetadataTemplate | None:
    if metadata_template_data is None:
        return None

    if assigned_to_object:
        check_metadata_template_permissions_for_object(
            content_type=get_content_type_for_object(assigned_to_object.get_content_type()),
            object_id=assigned_to_object.pk,
            user=user,
        )

    metadata_template = MetadataTemplate.objects.create(
        assigned_to_content_type=assigned_to_object.get_content_type() if assigned_to_object else None,
        assigned_to_object_id=assigned_to_object.pk if assigned_to_object else None,
        **metadata_template_data,
    )

    if metadata_template_fields:
        for metadata_template_field in metadata_template_fields:
            value = metadata_template_field.pop("value", None)
            field = MetadataTemplateField.objects.create(
                metadata_template=metadata_template,
                **metadata_template_field,
            )
            field.set_value(value)

    return metadata_template


def validate_metadata_integer(value: any):
    try:
        if not re.match(r"^[+-]?\d+([eE][+]?\d+)?$", str(value)):
            raise ValueError
    except ValueError:
        raise ValidationError(
            _("Metadata value for {key} must be an integer."),
        )


def validate_metadata_decimal(value: any):
    try:
        if not re.match(r"^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$", str(value)):
            raise ValueError
    except ValueError:
        raise ValidationError(
            _("Metadata value for {key} must be a decimal numeral."),
        )


def validate_metadata_datetime_format(value: any, datetime_format: str, error_msg: str):
    try:
        if not isinstance(value, str):
            raise ValueError

        datetime.strptime(value, datetime_format)
    except ValueError as e:
        raise ValidationError(
            error_msg if error_msg else str(e),
        )


def validate_metadata_datetime(value: any):
    validate_metadata_datetime_format(
        value=value,
        datetime_format="%Y-%m-%d %H:%M:%S",
        error_msg=_(
            "Metadata value for {key} must be in YYYY-MM-DD HH:MM:SS format and also be a valid date and time.",
        ),
    )


def validate_metadata_date(value: any):
    validate_metadata_datetime_format(
        value=value,
        datetime_format="%Y-%m-%d",
        error_msg=_("Metadata value for {key} must be in YYYY-MM-DD format and also be a valid date."),
    )


def validate_metadata_time(value: any):
    validate_metadata_datetime_format(
        value=value,
        datetime_format="%H:%M:%S",
        error_msg=_("Metadata value for {key} must be in HH:MM:SS format and also be a valid time."),
    )


def validate_metadata_selection(value: any, config: dict):
    try:
        options = config.get("options")

        if not isinstance(options, list):
            raise ValueError

        if value not in options:
            raise ValueError
    except ValueError:
        raise ValidationError(
            _("Metadata value for {key} must be included in the list of options."),
        )


def validate_metadata_wysiwyg(value: any):
    try:
        if not isinstance(value, dict):
            raise ValueError
    except ValueError:
        raise ValidationError(
            _("Metadata value for {key} must be a dict."),
        )


def validate_metadata_value(
    field: MetadataField | MetadataTemplateField,
    field_type: str,
    custom_key: str | None,
    value: any,
    config: dict,
):
    try:
        if field_type == MetadataFieldType.INTEGER:
            validate_metadata_integer(value=value)
        elif field_type == MetadataFieldType.DECIMAL:
            validate_metadata_decimal(value=value)
        elif field_type == MetadataFieldType.DATETIME:
            validate_metadata_datetime(value=value)
        elif field_type == MetadataFieldType.DATE:
            validate_metadata_date(value=value)
        elif field_type == MetadataFieldType.TIME:
            validate_metadata_time(value=value)
        elif field_type == MetadataFieldType.SELECTION:
            validate_metadata_selection(
                value=value,
                config=config,
            )
        elif field_type == MetadataFieldType.WYSIWYG:
            validate_metadata_wysiwyg(value=value)
    except ValueError as e:
        raise ValidationError(
            str(e).format(key=field.key if field else custom_key),
        )
