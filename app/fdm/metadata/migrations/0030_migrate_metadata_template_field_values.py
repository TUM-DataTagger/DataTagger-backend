from django.db import migrations

from fdm.metadata.enums import MetadataFieldType


def forwards_func(apps, schema_editor):
    MetadataTemplateField = apps.get_model("metadata", "MetadataTemplateField")
    metadata_template_field_list = MetadataTemplateField.objects.filter(
        value__isnull=True,
    )

    for metadata_template_field in metadata_template_field_list:
        metadata_template_field.value = (
            dict() if metadata_template_field.field_type == MetadataFieldType.WYSIWYG else dict(value=None)
        )
        metadata_template_field.save()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0029_migrate_metadata_values"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
