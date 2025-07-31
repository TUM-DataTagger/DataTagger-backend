from django.contrib.auth.models import GroupManager as DjangoGroupManager
from django.contrib.auth.models import UserManager as DjangoUserManager

from fdm.core.models.managers import BaseManager
from fdm.users.models.querysets import *

__all__ = [
    "UserManager",
    "GroupManager",
]


class UserManager(BaseManager.from_queryset(UserQuerySet), DjangoUserManager):
    pass


class GroupManager(BaseManager.from_queryset(GroupQuerySet), DjangoGroupManager):
    pass
