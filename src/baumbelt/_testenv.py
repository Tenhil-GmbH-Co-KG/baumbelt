import os
import sys


def running_under_test_runner() -> bool:
    """
    True only when the current process is `pytest`/`py.test`, or `manage.py test` / `django-admin test` - never for a
    real entrypoint such as gunicorn, `manage.py runserver` or an rq worker.
    """

    if "PYTEST_CURRENT_TEST" in os.environ:
        return True

    argv = sys.argv
    if not argv:
        return False

    prog = os.path.basename(argv[0])
    if prog in ("pytest", "py.test"):
        return True
    if prog in ("manage.py", "django-admin", "django-admin.py") and "test" in argv[1:]:
        return True

    return False
