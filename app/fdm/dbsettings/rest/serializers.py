from fdm.core.rest.base import BaseModelSerializer
from fdm.dbsettings.models import *

__all__ = [
    "SettingsSerializer",
]


class SettingsSerializer(BaseModelSerializer):
    class Meta:
        model = Setting
        fields = [
            "key",
            "value",
            "description",
            "public",
        ]
