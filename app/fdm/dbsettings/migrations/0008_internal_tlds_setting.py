from django.db import migrations


def forwards_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.create(
        key="INTERNAL_TLDS",
        value="",
        description="A list of top-level domains that are part of the organization. Required to restrict login methods to specific email addresses. One top-level domain per line.",
    )


def reverse_func(apps, schema_editor):
    Setting = apps.get_model("dbsettings", "Setting")
    Setting.objects.filter(
        key="INTERNAL_TLDS",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dbsettings", "0007_contact_email_address_setting"),
    ]

    operations = [
        migrations.RunPython(
            code=forwards_func,
            reverse_code=reverse_func,
        ),
    ]
