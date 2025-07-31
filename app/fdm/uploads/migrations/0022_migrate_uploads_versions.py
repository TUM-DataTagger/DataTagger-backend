from django.db import migrations


def forwards_func(apps, schema_editor):
    UploadsDataset = apps.get_model("uploads", "UploadsDataset")
    UploadsVersion = apps.get_model("uploads", "UploadsVersion")

    uploads_versions = UploadsVersion.objects.filter(dataset__isnull=True)

    for uploads_version in uploads_versions:
        uploads_version.dataset = UploadsDataset.objects.create(
            name=uploads_version.name,
            created_by=uploads_version.created_by,
            last_modified_by=uploads_version.last_modified_by,
        )
        uploads_version.save()


def reverse_func(apps, schema_editor):
    UploadsDataset = apps.get_model("uploads", "UploadsDataset")
    UploadsVersion = apps.get_model("uploads", "UploadsVersion")

    uploads_versions = UploadsVersion.objects.filter(publication_date__isnull=True)
    obsolete_datasets = []

    for uploads_version in uploads_versions:
        obsolete_datasets.append(uploads_version.dataset.pk)

        uploads_version.dataset = None
        uploads_version.save()

    UploadsDataset.objects.filter(pk__in=obsolete_datasets).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("uploads", "0021_uploadsdataset_publication_date"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
