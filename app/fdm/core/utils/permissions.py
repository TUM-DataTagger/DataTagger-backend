from django.conf import settings
from django.contrib.auth.management import create_permissions

__all__ = [
    "create_global_permissions_for_app",
    "get_permission_name",
]


def create_global_permissions_for_app(sender, **kwargs):
    # App is set by sender in post migrate
    app = sender
    # Add view permission to all models of this app
    for model_class in app.models.values():
        model_meta = model_class._meta

        for permission in settings.GLOBAL_MODEL_PERMISSIONS:
            if permission not in model_meta.default_permissions:
                model_meta.default_permissions += (permission,)

    create_permissions(app)


def get_permission_name(model_class, permission_name):
    # Permission for proxy model
    if getattr(model_class._meta, "proxy", False):
        return get_permission_name(model_class._meta.proxy_for_model, permission_name)

    return "{app_label}.{permission_name}_{model_name}".format(
        app_label=model_class._meta.app_label,
        model_name=model_class._meta.model_name,
        permission_name=permission_name,
    )
