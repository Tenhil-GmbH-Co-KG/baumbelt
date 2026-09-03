from unittest import TestCase
from unittest.mock import patch

from baumbelt.django.db.wait import db_migrated_to_current_state, wait_for_migrations


class DbMigratedToCurrentStateTestCase(TestCase):
    @patch("baumbelt.django.db.wait.settings")
    @patch("baumbelt.django.db.wait.call_command")
    def test_true_when_all_databases_migrated(self, call_command, settings):
        settings.DATABASES = {"default": {}}
        self.assertTrue(db_migrated_to_current_state())
        call_command.assert_called_once_with("migrate", database="default", interactive=False, check_unapplied=True)

    @patch("baumbelt.django.db.wait.settings")
    @patch("baumbelt.django.db.wait.call_command", side_effect=SystemExit(1))
    def test_false_when_a_database_has_unapplied_migrations(self, _call_command, settings):
        settings.DATABASES = {"default": {}}
        self.assertFalse(db_migrated_to_current_state())


class WaitForMigrationsTestCase(TestCase):
    @patch("baumbelt.django.db.wait.sleep")
    @patch("baumbelt.django.db.wait.db_migrated_to_current_state", return_value=True)
    def test_returns_immediately_when_already_migrated(self, _migrated, sleep):
        wait_for_migrations(timeout_secs=60)
        sleep.assert_not_called()

    @patch("baumbelt.django.db.wait.sleep")
    @patch("baumbelt.django.db.wait.db_migrated_to_current_state", return_value=False)
    def test_exits_on_timeout(self, _migrated, _sleep):
        with self.assertRaises(SystemExit):
            wait_for_migrations(timeout_secs=-1)

    @patch("baumbelt.django.db.wait.sleep")
    @patch("baumbelt.django.db.wait.db_migrated_to_current_state", return_value=False)
    def test_returns_early_when_should_stop(self, _migrated, sleep):
        wait_for_migrations(timeout_secs=60, should_stop=lambda: True)
        sleep.assert_not_called()
