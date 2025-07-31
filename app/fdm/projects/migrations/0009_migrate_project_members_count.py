from django.db import migrations


def forwards_func(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    ProjectMembership = apps.get_model("projects", "ProjectMembership")

    projects = Project.objects.all()

    for project in projects:
        project.members_count = ProjectMembership.objects.filter(
            project=project,
        ).count()

        project.save()


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0008_project_members_count"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
