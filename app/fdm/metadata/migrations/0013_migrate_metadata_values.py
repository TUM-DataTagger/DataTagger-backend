from django.db import migrations

from fdm.metadata.enums import MetadataFieldType


def forwards_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")
    metadata_list = Metadata.objects.all()

    for metadata in metadata_list:
        value = metadata.value

        try:
            if metadata.field_type == MetadataFieldType.INTEGER:
                value = int(value)
            elif metadata.field_type == MetadataFieldType.DECIMAL:
                value = float(value)
        except ValueError:
            pass

        metadata.value_json = dict(
            value=value,
        )
        metadata.save()


def reverse_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")
    metadata_list = Metadata.objects.all()

    for metadata in metadata_list:
        value = metadata.value_json.get("value")

        try:
            value = str(value)
        except ValueError:
            value = metadata.value_json

        metadata.value = value
        metadata.save()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0012_metadata_value_json_metadatatemplatefield_value_json"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
