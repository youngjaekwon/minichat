from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from django.http import HttpRequest

from apps.users.models import User


class AuthBackend(ModelBackend):
    """인증 백엔드."""

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs,
    ) -> User | None:
        # username 또는 email 파라미터 지원
        email = kwargs.get("email", username)
        if email is None or password is None:
            return None

        user = User.objects.get_by_email(email)
        if user is None:
            check_password(password, "dummy_hash")
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
