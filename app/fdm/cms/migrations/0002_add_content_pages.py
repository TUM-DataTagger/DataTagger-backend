from django.db import migrations


def create_content_pages(apps, schema_editor):
    Content = apps.get_model("cms", "Content")

    terms_page = Content.objects.filter(
        slug="terms-of-use",
    ).first()
    if not terms_page:
        Content.objects.create(
            slug="terms-of-use",
            name="Terms of use",
        )

    privacy_page = Content.objects.filter(
        slug="privacy-policy",
    ).first()
    if not privacy_page:
        Content.objects.create(
            slug="privacy-policy",
            name="Privacy policy",
        )

    accessibility_page = Content.objects.filter(
        slug="accessibility",
    ).first()
    if not accessibility_page:
        Content.objects.create(
            slug="accessibility",
            name="Accessibility",
        )


def remove_content_pages(apps, schema_editor):
    Content = apps.get_model("cms", "Content")

    Content.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_content_pages,
            remove_content_pages,
        ),
    ]
