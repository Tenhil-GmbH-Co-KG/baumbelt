from datetime import date, datetime, time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from baumbelt.django.apitokens.models import ApiToken


class Command(BaseCommand):
    help = "Create an API token for a user and print its key. The key can't be shown again."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("name", help="Where the token is used or stored, e.g. the client's secret.")
        parser.add_argument("--expires-at", type=date.fromisoformat, help="Expiry date (YYYY-MM-DD), at midnight.")

    def handle(self, *args, username: str, name: str, expires_at: date | None, **options):
        user_model = get_user_model()
        try:
            user = user_model._default_manager.get_by_natural_key(username)
        except user_model.DoesNotExist:
            raise CommandError(f"User {username!r} does not exist.")

        token = ApiToken(user=user, name=name)
        if expires_at:
            token.expires_at = datetime.combine(expires_at, time.min)
            if settings.USE_TZ:
                token.expires_at = timezone.make_aware(token.expires_at)
        try:
            key = token.set_new_key()
        except ImproperlyConfigured as e:
            raise CommandError(str(e))
        token.save()
        self.stdout.write(key)
