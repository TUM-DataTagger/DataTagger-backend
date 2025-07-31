import logging

from django.test import RequestFactory

from rest_framework_jwt.serializers import VerifyAuthTokenSerializer

logger = logging.getLogger(__name__)


def fake_rest_auth(auth_token, scope, *args, **kwargs):
    user = None
    request = None
    if auth_token:
        try:
            request_headers = dict()
            request_headers["REQUEST_METHOD"] = "GET"
            for header_name, header_value in scope["headers"]:
                header_name = header_name.decode().upper().replace("-", "_")
                request_headers["HTTP_" + header_name] = header_value.decode()
            request_headers["HTTP_AUTHORIZATION"] = f"Token {auth_token}"
            request = RequestFactory().request(**request_headers)
            data = {"token": auth_token}
            valid_data = VerifyAuthTokenSerializer().validate(data)
            user = valid_data["user"]
        except Exception as e:
            logger.error(e)
    return user, request
