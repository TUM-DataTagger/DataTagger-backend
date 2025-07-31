from django.db import migrations


def forwards_func(apps, schema_editor):
    Folder = apps.get_model("folders", "Folder")
    UploadsDataset = apps.get_model("uploads", "UploadsDataset")

    folders = Folder.objects.all()

    for folder in folders:
        folder.datasets_count = UploadsDataset.objects.filter(
            folder=folder,
        ).count()

        folder.save()


class Migration(migrations.Migration):
    dependencies = [
        ("folders", "0018_alter_folder_storage"),
        ("uploads", "0021_uploadsdataset_publication_date"),
        ("projects", "0011_project_is_deletable"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
