from datetime import timedelta
from functools import wraps

from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from baumbelt.django.apitokens.models import ApiToken, hash_key

# last_used_at is for humans, so it doesn't need a write on every request
LAST_USED_RESOLUTION = timedelta(minutes=1)


def get_bearer_key(request: HttpRequest) -> str | None:
    """Return the key of an `Authorization: Bearer <key>` header, or None."""
    scheme, _, key = request.headers.get("Authorization", "").partition(" ")
    key = key.strip()
    if scheme.lower() != "bearer" or not key:
        return None
    return key


def get_valid_token(key: str) -> ApiToken | None:
    """Return the unexpired token of an active user for the key, or None. Updates the token's last_used_at."""
    token = ApiToken.objects.unexpired().select_related("user").filter(key_hash=hash_key(key)).first()
    if token is None or not token.user.is_active:
        return None

    now = timezone.now()
    if token.last_used_at is None or now - token.last_used_at > LAST_USED_RESOLUTION:
        ApiToken.objects.filter(pk=token.pk).update(last_used_at=now)
        token.last_used_at = now
    return token


def authenticate_key(key: str) -> AbstractBaseUser | None:
    """Return the user of a valid token for the key, or None."""
    token = get_valid_token(key)
    return token.user if token else None


def authenticate_bearer(request: HttpRequest) -> AbstractBaseUser | None:
    """Return the user of a valid bearer token in the Authorization header, or None."""
    key = get_bearer_key(request)
    return authenticate_key(key) if key else None


def token_required(permission: str | None = None):
    """
    Require a bearer token for a plain Django view, optionally one whose user has the permission, e.g.
    "alerts.add_alert".

    Responds with 401 without a valid token and with 403 without the permission. Sets request.user.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            user = authenticate_bearer(request)
            if user is None:
                return HttpResponse(status=401, headers={"WWW-Authenticate": "Bearer"})
            if permission and not user.has_perm(permission):
                return HttpResponse(status=403)
            request.user = user
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
