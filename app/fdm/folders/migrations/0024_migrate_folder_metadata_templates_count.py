from django.db import migrations
from django.db.models import Q


def forwards_func(apps, schema_editor):
    from django.contrib.contenttypes.models import ContentType

    Project = apps.get_model("projects", "Project")
    Folder = apps.get_model("folders", "Folder")
    MetadataTemplate = apps.get_model("metadata", "MetadataTemplate")

    project_content_type = ContentType.objects.get_for_model(Project)
    folder_content_type = ContentType.objects.get_for_model(Folder)

    folders = Folder.objects.all()

    for folder in folders:
        # We are currently intentionally ignoring global templates
        folder.metadata_templates_count = MetadataTemplate.objects.filter(
            # Metadata templates assigned to the folder itself
            Q(
                assigned_to_content_type=folder_content_type.pk,
                assigned_to_object_id=folder.pk,
            )
            # Metadata templates assigned to the project the folder is part of
            | Q(
                assigned_to_content_type=project_content_type.pk,
                assigned_to_object_id=folder.project.pk,
            ),
        ).count()

        folder.save()


class Migration(migrations.Migration):
    dependencies = [
        ("folders", "0023_folder_metadata_templates_count"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
