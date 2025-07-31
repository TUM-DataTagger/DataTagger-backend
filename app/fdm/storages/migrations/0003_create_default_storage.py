from django.db import migrations

from fdm.storages.models import Storage as StorageModel


def forwards_func(apps, schema_editor):
    Storage = apps.get_model("storages", "Storage")
    Storage.objects.create(
        name="Default storage",
        storage_type=StorageModel.Type.LOCAL,
        default=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("storages", "0002_storage_default"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
