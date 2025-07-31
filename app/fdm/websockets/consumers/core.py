import abc
import logging

from channels.generic.websocket import JsonWebsocketConsumer
from django_userforeignkey.request import set_current_request

from fdm.websockets.authentication import fake_rest_auth

logger = logging.getLogger(__name__)


class AuthenticatedJsonWebsocketConsumer(JsonWebsocketConsumer):
    def connect(self, **kwargs):
        raise NotImplementedError()

    def disconnect(self, **kwargs):
        raise NotImplementedError()

    def receive_json(self, content, **kwargs):
        if "is_authenticated" in self.scope and self.scope["is_authenticated"]:
            request = self.scope["request"]
            set_current_request(request)
            return self.receive_json_authenticated(content, **kwargs)

        if "authorization" in content:
            self.scope["is_authenticated"] = False
            auth_token = content["authorization"]
            user, request = fake_rest_auth(auth_token, self.scope)
            self.scope["request"] = request
            self.scope["user"] = user
            set_current_request(request)
            if user and not user.is_anonymous:
                self.scope["is_authenticated"] = True
                self.send_json({"type": "auth_success", "data": {}})
                self.authentication_success(user)
            return
        logger.info("Got an unauthorized message")
        logger.debug(content)

    def authentication_success(self, user):
        raise NotImplementedError()

    @abc.abstractmethod
    def receive_json_authenticated(self, content, **kwargs):
        pass
