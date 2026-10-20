from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Authenticates accounts by their unique email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or '@' not in username or password is None:
            return None
        user = get_user_model().objects.filter(email__iexact=username).first()
        if user is None:
            return None
        username = user.get_username()
        return super().authenticate(request, username=username, password=password, **kwargs)
