import django
from django.conf import settings


def pytest_configure():
    if settings.configured:
        return

    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "baumbelt.django.db",
            "baumbelt.django.procs",
            "baumbelt.django.s3utils",
        ],
        USE_TZ=True,
    )
    django.setup()
