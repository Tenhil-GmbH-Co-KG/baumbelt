import django
from django.conf import settings


def pytest_configure():
    if settings.configured:
        return

    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.admin",
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.sessions",
            "django.contrib.messages",
            "baumbelt.django.apitokens",
            "baumbelt.django.db",
            "baumbelt.django.procs",
            "baumbelt.django.s3utils",
        ],
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ]
                },
            }
        ],
        ROOT_URLCONF="tests.urls",
        SECRET_KEY="baumbelt-tests",
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
        USE_TZ=True,
    )
    django.setup()
