from fdm.users.rest.serializers import UserSerializer

__all__ = [
    "jwt_response_payload_handler",
]


def jwt_response_payload_handler(token, user=None, request=None, *args, **kwargs):
    return {"token": token, "user": UserSerializer(user, context={"request": request}).data}
