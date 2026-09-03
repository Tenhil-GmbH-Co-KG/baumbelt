from django.core.management import BaseCommand

from baumbelt.django.db.wait import wait_for_migrations


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, **options):
        wait_for_migrations(timeout_secs=options["timeout"])
