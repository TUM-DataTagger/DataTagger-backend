from django.db import migrations

from fdm.metadata.enums import MetadataFieldType


def forwards_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")

    # Convert the most common keys to decimal field type
    Metadata.objects.filter(
        custom_key__in=[
            "EXIF_XRESOLUTION",
            "EXIF_YRESOLUTION",
        ],
    ).update(
        field_type=MetadataFieldType.DECIMAL,
    )

    # Convert the most common keys to integer field type
    Metadata.objects.filter(
        custom_key__in=[
            "EXIF_COMPRESSION",
            "EXIF_EXIFOFFSET",
            "EXIF_EXTRASAMPLES",
            "EXIF_FILLORDER",
            "EXIF_GPSINFO",
            "EXIF_IMAGELENGTH",
            "EXIF_IMAGENUMBER",
            "EXIF_IMAGEWIDTH",
            "EXIF_ORIENTATION",
            "EXIF_PHOTOMETRICINTERPRETATION",
            "EXIF_PLANARCONFIGURATION",
            "EXIF_PREDICTOR",
            "EXIF_RESOLUTIONUNIT",
            "EXIF_ROWSPERSTRIP",
            "EXIF_SAMPLESPERPIXEL",
            "EXIF_STRIPBYTECOUNTS",
            "EXIF_STRIPOFFSETS",
            "EXIF_YCBCRPOSITIONING",
        ],
    ).update(
        field_type=MetadataFieldType.INTEGER,
    )


def reverse_func(apps, schema_editor):
    Metadata = apps.get_model("metadata", "Metadata")
    metadata_list = Metadata.objects.all()

    for metadata in metadata_list:
        value = metadata.value_json.get("value")

        try:
            value = str(value)
        except ValueError:
            value = metadata.value_json

        metadata.value = value
        metadata.save()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0010_alter_metadata_field_type_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
