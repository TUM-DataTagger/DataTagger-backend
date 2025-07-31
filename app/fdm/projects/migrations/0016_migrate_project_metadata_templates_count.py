from django.db import migrations
from django.db.models import Q


def forwards_func(apps, schema_editor):
    from django.contrib.contenttypes.models import ContentType

    Project = apps.get_model("projects", "Project")
    MetadataTemplate = apps.get_model("metadata", "MetadataTemplate")

    content_type = ContentType.objects.get_for_model(Project)

    projects = Project.objects.all()

    for project in projects:
        # We are currently intentionally ignoring global templates
        project.metadata_templates_count = MetadataTemplate.objects.filter(
            # Metadata templates assigned to the folder itself
            Q(
                assigned_to_content_type=content_type.pk,
                assigned_to_object_id=project.pk,
            ),
        ).count()

        project.save()


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0015_project_metadata_templates_count"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
