from django.db import migrations

from fdm.metadata.enums import MetadataFieldType


def get_value_recursively(value):
    if isinstance(value, dict):
        return get_value_recursively(value.get("value"))

    return value


def forwards_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")
    metadata_list = Metadata.objects.exclude(
        field_type=MetadataFieldType.WYSIWYG,
    )

    for metadata in metadata_list:
        value = metadata.value.get("value")

        if isinstance(value, dict):
            metadata.value = {
                "value": get_value_recursively(value),
            }
            metadata.save()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0025_metadata_config_metadatatemplatefield_config"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
