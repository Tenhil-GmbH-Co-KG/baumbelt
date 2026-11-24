import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

DEFAULT_KEY_PREFIX = "bbt_"


def get_key_prefix() -> str:
    return getattr(settings, "BAUMBELT_API_TOKEN_PREFIX", DEFAULT_KEY_PREFIX)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class ApiTokenQuerySet(models.QuerySet):
    def unexpired(self):
        return self.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))


class ApiToken(models.Model):
    """
    A bearer token of a user, e.g. of another service that calls this one.

    Only the SHA-256 hash of the key is stored. The key is random, so a fast hash is enough. A password hasher like
    PBKDF2 would cost hundreds of milliseconds of CPU on every request.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_tokens")
    name = models.CharField(max_length=100, help_text="Where the token is used or stored, e.g. the client's secret.")
    key_hash = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Leave empty for a token that doesn't expire.")
    last_used_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = ApiTokenQuerySet.as_manager()

    class Meta:
        verbose_name = "API token"

    def __str__(self):
        return self.name

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    def set_new_key(self) -> str:
        """Generate a key, store its hash and return the key. It can't be recovered later."""
        key = get_key_prefix() + secrets.token_urlsafe(32)
        self.key_hash = hash_key(key)
        return key
