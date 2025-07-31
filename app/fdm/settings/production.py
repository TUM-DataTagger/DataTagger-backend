from .base import *

# ensure DEBUG is False in Production
DEBUG = False
TEMPLATE_DEBUG = DEBUG

########################################################################################################################
# Overwrite production only settings here
########################################################################################################################
EMAIL_USE_TLS = True


PRIVATE_DSS_MOUNT_PATH = "/dssmount"

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
]
