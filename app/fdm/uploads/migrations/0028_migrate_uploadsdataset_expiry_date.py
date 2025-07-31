from django.conf import settings
from django.db import migrations
from django.utils import timezone


def forwards_func(apps, schema_editor):
    UploadsDataset = apps.get_model("uploads", "UploadsDataset")

    datasets = UploadsDataset.objects.all()

    for dataset in datasets:
        if dataset.publication_date:
            dataset.expiry_date = None
        else:
            dataset.expiry_date = dataset.creation_date + timezone.timedelta(days=settings.DRAFT_FILES_MAX_LIFETIME)

        dataset.save()


def reverse_func(apps, schema_editor):
    UploadsDataset = apps.get_model("uploads", "UploadsDataset")

    datasets = UploadsDataset.objects.all()

    for dataset in datasets:
        dataset.expiry_date = None
        dataset.save()


class Migration(migrations.Migration):
    dependencies = [
        ("uploads", "0027_uploadsdataset_expiry_date"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
