from django.db import migrations


def forwards_func(apps, schema_editor):
    MetadataTemplateField = apps.get_model("metadata", "MetadataTemplateField")
    MetadataTemplateField.objects.all().update(
        value="",
    )


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
        ("metadata", "0016_migrate_metadata_values"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
