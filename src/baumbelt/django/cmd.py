import logging
import signal

from django.core.management import BaseCommand

from baumbelt._testenv import running_under_test_runner as _running_under_test_runner
from baumbelt.django.db.wait import wait_for_migrations

logger = logging.getLogger(__name__)


class GracefulShutdown(Exception):
    """Raised on SIGTERM so the process exits with a clear stack trace instead of dying to SIGKILL."""


class GracefulCommand(BaseCommand):
    """`BaseCommand` subclass that installs a SIGTERM handler around `execute()`.

    Requires the command's process to be PID 1 (plain argv `command:` in k8s, no `bash -c` wrapper)
    for the signal to actually reach it.
    """

    require_db_migrated = True
    migration_wait_timeout_secs = 60

    def execute(self, *args, **options):
        self.shutdown_requested = False
        previous_handler = signal.signal(signal.SIGTERM, self._handle_sigterm)
        try:
            # Under a test runner the DB is already migrated by the test setup, so waiting is pointless - and
            # actively harmful under Django's per-TestCase DB isolation, which raises DatabaseOperationForbidden
            # for any database not declared on `databases`, making the migrate-check poll forever until timeout.
            if self.require_db_migrated and not _running_under_test_runner():
                wait_for_migrations(
                    timeout_secs=self.migration_wait_timeout_secs,
                    should_stop=lambda: self.shutdown_requested,
                )
            return super().execute(*args, **options)
        finally:
            signal.signal(signal.SIGTERM, previous_handler)

    def _handle_sigterm(self, signum, frame):
        self.shutdown_requested = True
        logger.warning("SIGTERM received, shutting down")
        self.on_sigterm()
        raise GracefulShutdown()

    def on_sigterm(self):
        """Override for teardown logic to run before `GracefulShutdown` propagates."""
