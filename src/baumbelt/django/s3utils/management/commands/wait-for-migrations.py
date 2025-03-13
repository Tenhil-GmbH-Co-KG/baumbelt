import logging
import sys
from datetime import timedelta
from time import sleep

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, **options):
        start = timezone.now()
        timeout_secs = options["timeout"]
        timeout = start + timedelta(seconds=timeout_secs)
        while not self.db_migrated_to_current_state():
            if timezone.now() > timeout:
                logger.warning(f"exceeded timeout ({timeout_secs}s) - db is still not migrated")
                sys.exit(1)
            sleep(2)
        logger.debug(f"ready after {timezone.now() - start} - db is migrated")

    def db_migrated_to_current_state(self) -> bool:
        status_map: dict[str, bool | str] = {}
        for db in settings.DATABASES.keys():
            try:
                call_command("migrate", database=db, interactive=False, check_unapplied=True)
            except (SystemExit, Exception) as exc:
                if isinstance(exc, SystemExit) and exc.code == 1:
                    status_map[db] = False
                else:
                    status_map[db] = f"{type(exc).__name__} - {exc}"
            else:
                status_map[db] = True

        if any(status is not True for status in status_map.values()):
            logger.debug(f"db migration status: {status_map}")
            return False

        return True
