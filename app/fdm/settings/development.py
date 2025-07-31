from .base import *

# settings specific for the development setup


# for static files in a local docker environment
MIDDLEWARE += [
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATE_DEBUG = True

# add debug toolbar to installed_apps and middleware if available
if DEBUG:
    try:
        import debug_toolbar

        # if we got this far, debug toolbar is available
        # Enable debug toolbar callback (needed because we are within a docker instance)
        DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda x: DEBUG}

        # add to installed apps and enable the middleware
        INSTALLED_APPS += ("debug_toolbar",)
        MIDDLEWARE += [
            "debug_toolbar.middleware.DebugToolbarMiddleware",
        ]
    except ImportError:  # ignore
        pass
