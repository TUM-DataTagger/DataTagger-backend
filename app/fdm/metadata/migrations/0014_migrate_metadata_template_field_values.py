from django.db import migrations

from fdm.metadata.enums import MetadataFieldType


def forwards_func(apps, schema_editor):
    MetadataTemplateField = apps.get_model("metadata", "MetadataTemplateField")
    metadata_template_field_list = MetadataTemplateField.objects.all()

    for metadata_template_field in metadata_template_field_list:
        value = metadata_template_field.value

        try:
            if metadata_template_field.field_type == MetadataFieldType.INTEGER:
                value = int(value)
            elif metadata_template_field.field_type == MetadataFieldType.DECIMAL:
                value = float(value)
        except ValueError:
            pass

        metadata_template_field.value_json = dict(
            value=value,
        )
        metadata_template_field.save()


def reverse_func(apps, schema_editor):
    MetadataTemplateField = apps.get_model("metadata", "MetadataTemplateField")
    metadata_template_field_list = MetadataTemplateField.objects.all()

    for metadata_template_field in metadata_template_field_list:
        value = metadata_template_field.value_json.get("value")

        try:
            value = str(value)
        except ValueError:
            value = metadata_template_field.value_json

        metadata_template_field.value = value
        metadata_template_field.save()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0013_migrate_metadata_values"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
