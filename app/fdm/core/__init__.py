from django.db.models import options

default_app_config = "fdm.core.apps.CoreConfig"

# extend allowed meta options for models
# used to specify fields for a default __str__ method
options.DEFAULT_NAMES = options.DEFAULT_NAMES + (
    "str_fields",
    "str_delimiter",
)
