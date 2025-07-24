from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from photos.models import Token


class TokenBackEnd(BaseBackend):
    def authenticate(self, request, token=None):
        try:
            token_obj = Token.objects.get(uuid=token)
            return token_obj.user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
