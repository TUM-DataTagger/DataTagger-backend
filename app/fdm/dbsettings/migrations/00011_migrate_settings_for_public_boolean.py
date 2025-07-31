from django.db import migrations


def forwards_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.exclude(
        key__in=[
            "MAX_LOCK_TIME",
            "INTERNAL_TLDS",
        ],
    ).update(public=True)


def reverse_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.all().update(public=False)


class Migration(migrations.Migration):
    dependencies = [
        ("dbsettings", "0010_setting_public"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
