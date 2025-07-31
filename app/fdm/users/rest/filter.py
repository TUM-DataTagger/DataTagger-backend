from django.contrib.auth import get_user_model

from fdm.core.rest.base import BaseFilter

User = get_user_model()

__all__ = [
    "UserFilter",
]


class UserFilter(BaseFilter):
    class Meta:
        model = User
        fields = {
            "username": BaseFilter.TEXT_FILTER,
        }
