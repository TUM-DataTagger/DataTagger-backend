from django.db import migrations


def forwards_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.create(
        key="APP_TITLE",
        value="FDM",
        description="The title of the application",
    )


def reverse_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.filter(
        key="APP_TITLE",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dbsettings", "0003_alter_setting_key"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
