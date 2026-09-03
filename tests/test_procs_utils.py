from unittest import TestCase
from unittest.mock import patch

from baumbelt.django.procs.utils import list_running_management_commands


class FakeProcess:
    def __init__(self, info: dict):
        self.info = info


def fake_process_iter(_attrs):
    return iter(
        [
            FakeProcess({"pid": 111, "cmdline": ["python", "manage.py", "some-cronjob"], "create_time": 900.0}),
            FakeProcess({"pid": 222, "cmdline": ["nginx"], "create_time": 900.0}),
            FakeProcess({"pid": 333, "cmdline": ["python", "manage.py"], "create_time": 900.0}),
            FakeProcess({"pid": 444, "cmdline": ["python", "manage.py", "self"], "create_time": 900.0}),
        ]
    )


class ListRunningManagementCommandsTestCase(TestCase):
    @patch("baumbelt.django.procs.utils.os.getpid", return_value=444)
    @patch("baumbelt.django.procs.utils.time.time", return_value=1000.0)
    @patch("baumbelt.django.procs.utils.psutil.process_iter", side_effect=fake_process_iter)
    def test_filters_own_pid_non_manage_py_and_missing_command_arg(self, *_mocks):
        result = list_running_management_commands()

        self.assertEqual(result, [{"pid": 111, "cmd_name": "some-cronjob", "running_seconds": 100}])
