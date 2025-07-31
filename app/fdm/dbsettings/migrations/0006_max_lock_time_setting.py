from django.db import migrations


def forwards_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.create(
        key="MAX_LOCK_TIME",
        value="20",
        description="Time in minutes for how long a data record remains locked",
    )


def reverse_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.filter(
        key="MAX_LOCK_TIME",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dbsettings", "0005_alter_setting_value"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
