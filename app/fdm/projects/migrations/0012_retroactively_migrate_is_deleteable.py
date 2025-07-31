from django.db import migrations


def forwards_func(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Folder = apps.get_model("folders", "Folder")

    projects = Project.objects.all()

    for project in projects:
        folders = Folder.objects.filter(project=project)

        for folder in folders:
            if folder.datasets_count:
                project.is_deletable = not bool(folder.datasets_count)
                project.save()
                break


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0011_project_is_deletable"),
        ("folders", "0019_recalculate_folder_datasets_count"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
