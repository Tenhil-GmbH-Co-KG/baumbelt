from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

from baumbelt.django.apitokens.auth import get_bearer_key, get_valid_token


class ApiTokenAuthentication(BaseAuthentication):
    """
    Authenticate `Authorization: Bearer <key>` against ApiToken. Sets request.user to the token's user and
    request.auth to the token.

    Requests without a bearer key are left to the other authentication classes. To accept the key in another place
    too, e.g. in a legacy header during a migration, override get_key().
    """

    keyword = "Bearer"

    def get_key(self, request) -> str | None:
        return get_bearer_key(request)

    def authenticate(self, request):
        key = self.get_key(request)
        if not key:
            return None

        token = get_valid_token(key)
        if token is None:
            raise exceptions.AuthenticationFailed("Invalid token.")
        return token.user, token

    def authenticate_header(self, request):
        return self.keyword


def HasPerm(*perms: str) -> type[BasePermission]:
    """
    Return a DRF permission class that requires an authenticated user with all the permissions, e.g.
    `permission_classes = (HasPerm("aim.add_job"),)`.
    """

    class _HasPerm(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and user.has_perms(perms))

    _HasPerm.__name__ = _HasPerm.__qualname__ = f"HasPerm({', '.join(perms)})"
    return _HasPerm
