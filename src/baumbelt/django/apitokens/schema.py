from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ApiTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "baumbelt.django.apitokens.drf.ApiTokenAuthentication"
    name = "ApiTokenAuthentication"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer"}
