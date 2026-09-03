import json

from django.core.management import BaseCommand

from baumbelt.django.procs.utils import list_running_management_commands


class Command(BaseCommand):
    help = "List currently running `manage.py <command>` processes (e.g. cronjobs) on this host/container."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="output as JSON")

    def handle(self, *args, **options):
        running = list_running_management_commands()

        if options["json"]:
            print(json.dumps({"results": running}))
            return

        if not running:
            print("no management commands currently running")
            return

        for entry in running:
            print(f"{entry['cmd_name']} (pid {entry['pid']}, running for {entry['running_seconds']}s)")
