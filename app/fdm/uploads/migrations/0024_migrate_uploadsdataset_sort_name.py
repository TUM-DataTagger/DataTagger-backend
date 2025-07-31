from django.db import migrations


def forwards_func(apps, schema_editor):
    from django.contrib.contenttypes.models import ContentType

    UploadsDataset = apps.get_model("uploads", "UploadsDataset")
    UploadsVersion = apps.get_model("uploads", "UploadsVersion")
    UploadsVersionFile = apps.get_model("uploads", "UploadsVersionFile")
    Metadata = apps.get_model("metadata", "Metadata")

    content_type = ContentType.objects.get_for_model(UploadsVersionFile)
    datasets = UploadsDataset.objects.all()

    for dataset in datasets:
        display_name = str(dataset.pk)

        if dataset.name:
            display_name = dataset.name
        else:
            latest_version = (
                UploadsVersion.objects.filter(
                    dataset=dataset,
                )
                .order_by("-creation_date")
                .first()
            )

            if latest_version and latest_version.version_file:
                original_filename = Metadata.objects.filter(
                    assigned_to_content_type=content_type.pk,
                    assigned_to_object_id=latest_version.version_file.pk,
                    custom_key="FILE_NAME",
                ).first()

                if original_filename:
                    display_name = original_filename.value

        dataset.display_name = display_name
        dataset.save()


def reverse_func(apps, schema_editor):
    UploadsDataset = apps.get_model("uploads", "UploadsDataset")

    datasets = UploadsDataset.objects.all()

    for dataset in datasets:
        dataset.display_name = None
        dataset.save()


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("metadata", "0007_migrate_metadata_proxy_models"),
        ("uploads", "0023_uploadsdataset_display_name"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
