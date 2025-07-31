from django.apps import AppConfig
from django.db.models.signals import post_migrate

from fdm.core.utils.permissions import create_global_permissions_for_app

__all__ = [
    "ShibbolethConfig",
]


class ShibbolethConfig(AppConfig):
    name = "fdm.shibboleth"

    def ready(self):
        post_migrate.connect(
            create_global_permissions_for_app,
            sender=self,
        )

        # import handlers here so they are registered when the application starts
        import fdm.shibboleth.handlers
