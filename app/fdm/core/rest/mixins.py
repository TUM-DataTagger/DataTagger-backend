from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, inline_serializer

from fdm.core.rest.serializers import LockStatusSerializer

__all__ = [
    "LockStatusMixin",
    "LockMixin",
    "UnlockMixin",
]


class LockStatusMixin:
    """
    Lock status of a model instance.
    """

    @extend_schema(
        responses={
            200: LockStatusSerializer,
        },
        methods=["GET"],
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="status",
        url_name="status",
        filterset_class=None,
        pagination_class=None,
    )
    def status(self, request, *args, **kwargs):
        instance = self.get_object()

        return Response(
            data=LockStatusSerializer(instance).data,
            status=status.HTTP_200_OK,
        )


class LockMixin:
    """
    Lock action for a model instance.
    """

    @extend_schema(
        request=inline_serializer(
            name="LockSerializer",
            fields={},
        ),
        responses={
            201: LockStatusSerializer,
        },
        methods=["POST"],
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="lock",
        url_name="lock",
        filterset_class=None,
        pagination_class=None,
    )
    def lock(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.locked and not instance.is_locked_by_myself():
            return Response(
                data={
                    "lock": _("You must not edit an element which has been locked by another user."),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        instance.lock()

        return Response(
            data=LockStatusSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


class UnlockMixin:
    """
    Unlock action for a model instance.
    """

    @extend_schema(
        request=inline_serializer(
            name="UnlockSerializer",
            fields={},
        ),
        responses={
            201: LockStatusSerializer,
        },
        methods=["POST"],
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="unlock",
        url_name="unlock",
        filterset_class=None,
        pagination_class=None,
    )
    def unlock(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.locked and not instance.is_locked_by_myself():
            return Response(
                data={
                    "unlock": _("You must not edit an element which has been locked by another user."),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        instance.unlock()

        return Response(
            data=LockStatusSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )
