from django.core.management.templates import TemplateCommand


class Command(TemplateCommand):
    """
    Implemented as recommended in https://code.djangoproject.com/ticket/20741
    """

    help = (
        "Extends the django manage.py startapp command to create a new app with "
        "extra context variables that can be used inside the template."
    )
    missing_args_message = "You must provide an application name."

    def handle(self, **options):
        app_slug = "fdm"
        app_name = options.pop("name")
        target = options.pop("directory")
        super().handle("app", app_name, target, app_slug=app_slug, **options)
