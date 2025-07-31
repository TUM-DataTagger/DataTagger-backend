from django.db import migrations


def set_default_storage(apps, schema_editor):
    DynamicStorage = apps.get_model("storages", "DynamicStorage")
    DynamicStorage.objects.filter(default=True).update(mounted=True, approved=True)


class Migration(migrations.Migration):
    dependencies = [
        ("storages", "0008_dynamicstorage_approved_dynamicstorage_mounted"),
    ]

    operations = [
        migrations.RunPython(
            code=set_default_storage,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
