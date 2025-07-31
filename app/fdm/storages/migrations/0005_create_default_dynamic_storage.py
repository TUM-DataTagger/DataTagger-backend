from django.db import migrations

from fdm.storages.models.mappings import DEFAULT_STORAGE_TYPE, STORAGE_PROVIDER_MAP


def forwards_func(apps, schema_editor):
    """
    Create DynamicStorage records using the same IDs as the existing Storage records
    """
    Storage = apps.get_model("storages", "Storage")
    DynamicStorage = apps.get_model("storages", "DynamicStorage")

    storage_config = STORAGE_PROVIDER_MAP[DEFAULT_STORAGE_TYPE]

    # Copy over each Storage record to DynamicStorage
    for storage in Storage.objects.all():
        DynamicStorage.objects.create(
            id=storage.id,  # Use same ID
            name=storage.name,
            description={
                "migrated_from": "Storage",
                "original_type": storage.storage_type,
                "local": storage_config["local"],
            },
            storage_type=DEFAULT_STORAGE_TYPE,
            default=storage.default,
            created_by=storage.created_by,
            last_modified_by=storage.last_modified_by,
        )


def reverse_func(apps, schema_editor):
    """
    Remove all DynamicStorage records
    """
    DynamicStorage = apps.get_model("storages", "DynamicStorage")
    DynamicStorage.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("storages", "0004_dynamicstorage"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
