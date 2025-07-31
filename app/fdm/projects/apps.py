from django.apps import AppConfig
from django.db.models.signals import post_migrate

from fdm.core.utils.permissions import create_global_permissions_for_app


class ProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fdm.projects"

    def ready(self):
        post_migrate.connect(
            create_global_permissions_for_app,
            sender=self,
        )

        # import signal handlers
        import fdm.projects.handlers
