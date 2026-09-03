import signal
from unittest import TestCase
from unittest.mock import patch

from django.core.management import call_command

from baumbelt.django.cmd import GracefulCommand, GracefulShutdown


class WithMigrationWait(GracefulCommand):
    def handle(self, *args, **options):
        return "handled"


class WithoutMigrationWait(GracefulCommand):
    require_db_migrated = False

    def handle(self, *args, **options):
        return "handled"


class GracefulCommandExecuteTestCase(TestCase):
    @patch("baumbelt.django.cmd._running_under_test_runner", return_value=False)
    @patch("baumbelt.django.cmd.wait_for_migrations")
    def test_waits_for_migrations_by_default_outside_test_runner(self, wait_for_migrations, _running_under_test):
        call_command(WithMigrationWait())
        wait_for_migrations.assert_called_once()

    @patch("baumbelt.django.cmd.wait_for_migrations")
    def test_skips_migration_wait_when_disabled(self, wait_for_migrations):
        call_command(WithoutMigrationWait())
        wait_for_migrations.assert_not_called()

    @patch("baumbelt.django.cmd._running_under_test_runner", return_value=True)
    @patch("baumbelt.django.cmd.wait_for_migrations")
    def test_skips_migration_wait_under_test_runner(self, wait_for_migrations, _running_under_test):
        # Migrations are already applied by the test setup, and under Django's per-TestCase DB isolation the
        # migrate-check would poll forever against any undeclared database until it times out.
        call_command(WithMigrationWait())
        wait_for_migrations.assert_not_called()

    def test_restores_previous_sigterm_handler_after_execute(self):
        original_handler = signal.getsignal(signal.SIGTERM)
        call_command(WithoutMigrationWait())
        self.assertEqual(signal.getsignal(signal.SIGTERM), original_handler)


class GracefulCommandSigtermTestCase(TestCase):
    def test_handle_sigterm_sets_flag_calls_hook_and_raises(self):
        command = WithoutMigrationWait()
        command.shutdown_requested = False
        command.on_sigterm = lambda: setattr(command, "hook_called", True)

        with self.assertRaises(GracefulShutdown):
            command._handle_sigterm(signal.SIGTERM, None)

        self.assertTrue(command.shutdown_requested)
        self.assertTrue(command.hook_called)
