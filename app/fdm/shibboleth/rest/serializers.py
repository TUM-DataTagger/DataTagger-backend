from rest_framework import serializers

from fdm.core.rest.serializers import UserResponseSerializer


class ShibbolethStartSerializer(serializers.Serializer):
    shibboleth_login_url = serializers.URLField(
        required=True,
    )

    auth_code = serializers.CharField(
        required=True,
    )


class ShibbolethTargetSerializer(serializers.Serializer):
    user = UserResponseSerializer(
        read_only=True,
    )

    redirect_url = serializers.URLField(
        required=True,
    )
