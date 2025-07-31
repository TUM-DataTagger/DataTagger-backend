from django.db import migrations


def forwards_func(apps, schema_editor):
    from django.contrib.contenttypes.models import ContentType

    update_model_pairs = []

    try:
        update_model_pairs.append(
            [
                apps.get_model("projects", "Project"),
                apps.get_model("projects", "ProjectMetadata"),
            ],
        )
    except LookupError:
        pass

    try:
        update_model_pairs.append(
            [
                apps.get_model("folders", "Folder"),
                apps.get_model("folders", "FolderMetadata"),
            ],
        )
    except LookupError:
        pass

    try:
        update_model_pairs.append(
            [
                apps.get_model("uploads", "UploadsVersion"),
                apps.get_model("uploads", "UploadsVersionMetadata"),
            ],
        )
    except LookupError:
        pass

    try:
        update_model_pairs.append(
            [
                apps.get_model("uploads", "UploadsVersionFile"),
                apps.get_model("uploads", "UploadsVersionFileMetadata"),
            ],
        )
    except LookupError:
        pass

    for update_model_pair in update_model_pairs:
        metadata_records = update_model_pair[1].objects.all()

        metadata_records.update(
            assigned_to_content_type=ContentType.objects.get_for_model(update_model_pair[0]),
        )

        for metadata in metadata_records:
            metadata.assigned_to_object_id = metadata.relation.pk
            metadata.save()


def reverse_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")
    Metadata.objects.all().update(
        assigned_to_content_type=None,
        assigned_to_object_id=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0006_metadata_assigned_to_content_type_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
