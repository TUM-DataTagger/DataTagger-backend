from django.db import migrations

from fdm.uploads.models import UploadsVersionFile as UploadsVersionFileModel


def forwards_func(apps, schema_editor):
    UploadsVersionFile = apps.get_model("uploads", "UploadsVersionFile")
    UploadsVersionFile.objects.filter(
        status=UploadsVersionFileModel.Status.ERROR,
    ).update(
        status=UploadsVersionFileModel.Status.SCHEDULED,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("file_parser", "0006_alter_fileparser_parser_type"),
        ("metadata", "0026_migrate_metadata_values"),
        ("uploads", "0030_alter_uploadsversionfile_uploaded_file"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
