from django.db import migrations

from fdm.metadata.enums import MetadataFieldType


def forwards_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")
    metadata_list = Metadata.objects.filter(
        value__isnull=True,
    )

    for metadata in metadata_list:
        metadata.value = dict() if metadata.field_type == MetadataFieldType.WYSIWYG else dict(value=None)
        metadata.save()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0028_alter_metadata_value_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
