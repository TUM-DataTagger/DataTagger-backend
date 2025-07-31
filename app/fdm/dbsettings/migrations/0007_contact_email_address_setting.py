from django.db import migrations


def forwards_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.create(
        key="CONTACT_EMAIL",
        value="",
        description="Email address displayed to users in the contact information section",
    )


def reverse_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.filter(
        key="CONTACT_EMAIL",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dbsettings", "0006_max_lock_time_setting"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
