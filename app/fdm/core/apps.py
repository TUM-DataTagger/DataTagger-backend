from django.apps import AppConfig
from django.db.models.signals import post_migrate

from fdm.core.utils.permissions import create_global_permissions_for_app

__all__ = [
    "CoreConfig",
]


class CoreConfig(AppConfig):
    name = "fdm.core"

    def ready(self):
        post_migrate.connect(
            create_global_permissions_for_app,
            sender=self,
        )

        # import signal handlers
        import fdm.core.handlers
