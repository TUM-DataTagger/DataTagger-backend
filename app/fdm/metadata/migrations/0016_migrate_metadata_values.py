from django.db import migrations


def forwards_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")
    Metadata.objects.all().update(
        value=None,
    )


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
        ("metadata", "0015_alter_metadata_value"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
