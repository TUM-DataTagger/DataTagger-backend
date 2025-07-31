from django.db import migrations


def forwards_func(apps, schema_editor):
    Folder = apps.get_model("folders", "Folder")
    Storage = apps.get_model("storages", "Storage")

    folders = Folder.objects.all()

    try:
        default_storage = Storage.objects.get(default=True)

        for folder in folders:
            folder.storage = default_storage
            folder.save()
    except Storage.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("storages", "0003_create_default_storage"),
        ("folders", "0016_alter_folder_storage"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
