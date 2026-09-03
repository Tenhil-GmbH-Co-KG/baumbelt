import logging
import sys
from collections.abc import Callable
from datetime import timedelta
from time import sleep

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)


def db_migrated_to_current_state() -> bool:
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


def wait_for_migrations(timeout_secs: int = 60, should_stop: Callable[[], bool] | None = None) -> None:
    """Block until all configured databases are migrated, or exit(1) on timeout.

    `should_stop` is polled on each iteration (e.g. `GracefulCommand.shutdown_requested`)
    so a SIGTERM arriving mid-wait exits cleanly instead of spinning until SIGKILL.
    """
    start = timezone.now()
    timeout = start + timedelta(seconds=timeout_secs)
    while not db_migrated_to_current_state():
        if should_stop is not None and should_stop():
            logger.warning("shutdown requested - aborting migration wait")
            return
        if timezone.now() > timeout:
            logger.warning(f"exceeded timeout ({timeout_secs}s) - db is still not migrated")
            sys.exit(1)
        sleep(2)
    logger.debug(f"ready after {timezone.now() - start} - db is migrated")
