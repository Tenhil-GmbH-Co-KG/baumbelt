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
    @patch("baumbelt.django.cmd.wait_for_migrations")
    def test_waits_for_migrations_by_default(self, wait_for_migrations):
        call_command(WithMigrationWait())
        wait_for_migrations.assert_called_once()

    @patch("baumbelt.django.cmd.wait_for_migrations")
    def test_skips_migration_wait_when_disabled(self, wait_for_migrations):
        call_command(WithoutMigrationWait())
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
