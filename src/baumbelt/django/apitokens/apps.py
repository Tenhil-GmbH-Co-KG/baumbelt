from django.apps import AppConfig


class ApiTokensConfig(AppConfig):
    name = "baumbelt.django.apitokens"
    label = "apitokens"
    verbose_name = "API tokens"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        try:
            import drf_spectacular  # noqa: F401
        except ImportError:
            return

        # registers the OpenAPI security scheme of ApiTokenAuthentication
        from baumbelt.django.apitokens import schema  # noqa: F401
