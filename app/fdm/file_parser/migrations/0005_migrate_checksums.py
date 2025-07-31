from django.db import migrations

from fdm.file_parser.models import FileParser as FileParserModel


def forwards_func(apps, schema_editor):
    FileParser = apps.get_model("file_parser", "FileParser")
    FileParser.objects.filter(
        parser_type__startswith="CHECKSUM",
    ).exclude(
        parser_type=FileParserModel.Type.CHECKSUM_SHA256,
    ).delete()

    Metadata = apps.get_model("metadata", "Metadata")
    Metadata.objects.filter(
        custom_key__startswith="CHECKSUM",
    ).exclude(
        custom_key=FileParserModel.Type.CHECKSUM_SHA256,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("file_parser", "0004_alter_fileparser_parser_type"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
