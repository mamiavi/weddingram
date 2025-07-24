from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from photos.models import Token


class TokenBackEnd(BaseBackend):
    def authenticate(self, request, token=None):
        try:
            Token.objects.get(uuid=token)
            return User.objects.get(username='invitado')
        except Token.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
