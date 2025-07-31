from django.db import migrations


def forwards_func(apps, schema_editor):
    Folder = apps.get_model("folders", "Folder")
    FolderPermission = apps.get_model("folders", "FolderPermission")

    folders = Folder.objects.all()

    for folder in folders:
        folder.members_count = FolderPermission.objects.filter(
            folder=folder,
        ).count()

        folder.save()


class Migration(migrations.Migration):
    dependencies = [
        ("folders", "0010_folder_datasets_count_folder_members_count"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
