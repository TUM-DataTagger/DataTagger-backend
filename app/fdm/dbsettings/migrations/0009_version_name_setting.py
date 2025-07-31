from django.db import migrations


def forwards_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.create(
        key="VERSION_NAME",
        value="",
        description="The name of the version currently deployed",
    )


def reverse_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.filter(
        key="VERSION_NAME",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dbsettings", "0008_internal_tlds_setting"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
