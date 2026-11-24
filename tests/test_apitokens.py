from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth.models import Permission, User
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import setup_test_environment, teardown_test_environment
from django.urls import reverse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from baumbelt.django.apitokens.auth import authenticate_bearer, get_bearer_key, token_required
from baumbelt.django.apitokens.drf import ApiTokenAuthentication, HasPerm
from baumbelt.django.apitokens.models import ApiToken, hash_key


@pytest.fixture(scope="module", autouse=True)
def database():
    setup_test_environment()
    call_command("migrate", verbosity=0)
    yield
    teardown_test_environment()


def create_token(user: User, **kwargs) -> tuple[ApiToken, str]:
    token = ApiToken(user=user, name="test", **kwargs)
    key = token.set_new_key()
    token.save()
    return token, key


def bearer(key: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {key}"}


class ApiTokenModelTestCase(TestCase):
    def test_stores_only_the_hash_of_the_key(self):
        token, key = create_token(User.objects.create(username="client"))

        self.assertTrue(key.startswith("test_"))
        self.assertEqual(token.key_hash, hash_key(key))
        self.assertNotIn(key, str(ApiToken.objects.values().get()))

    def test_requires_key_prefix_setting(self):
        with override_settings():
            del settings.BAUMBELT_API_TOKEN_PREFIX
            with self.assertRaises(ImproperlyConfigured):
                ApiToken().set_new_key()

        with override_settings(BAUMBELT_API_TOKEN_PREFIX=""), self.assertRaises(ImproperlyConfigured):
            ApiToken().set_new_key()

    def test_is_expired(self):
        now = timezone.now()
        self.assertFalse(ApiToken(expires_at=None).is_expired)
        self.assertFalse(ApiToken(expires_at=now + timedelta(minutes=1)).is_expired)
        self.assertTrue(ApiToken(expires_at=now - timedelta(minutes=1)).is_expired)


class AuthenticateBearerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="client")
        self.token, self.key = create_token(self.user)
        self.factory = RequestFactory()

    def authenticate(self, **headers):
        return authenticate_bearer(self.factory.get("/", **headers))

    def test_returns_user_of_valid_key(self):
        self.assertEqual(self.authenticate(**bearer(self.key)), self.user)

    def test_scheme_is_case_insensitive(self):
        self.assertEqual(self.authenticate(HTTP_AUTHORIZATION=f"bearer {self.key}"), self.user)

    def test_returns_none_without_valid_bearer_key(self):
        self.assertIsNone(self.authenticate())
        self.assertIsNone(self.authenticate(HTTP_AUTHORIZATION="Bearer "))
        self.assertIsNone(self.authenticate(HTTP_AUTHORIZATION=f"Basic {self.key}"))
        self.assertIsNone(self.authenticate(**bearer(self.key + "x")))

    def test_returns_none_for_inactive_user(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertIsNone(self.authenticate(**bearer(self.key)))

    def test_returns_none_for_expired_token(self):
        ApiToken.objects.filter(pk=self.token.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(self.authenticate(**bearer(self.key)))

    def test_accepts_token_that_expires_in_the_future(self):
        ApiToken.objects.filter(pk=self.token.pk).update(expires_at=timezone.now() + timedelta(days=1))
        self.assertEqual(self.authenticate(**bearer(self.key)), self.user)

    def test_updates_last_used_at_at_most_once_per_minute(self):
        self.authenticate(**bearer(self.key))
        first_use = ApiToken.objects.get().last_used_at
        self.assertIsNotNone(first_use)

        self.authenticate(**bearer(self.key))
        self.assertEqual(ApiToken.objects.get().last_used_at, first_use)

        ApiToken.objects.update(last_used_at=first_use - timedelta(minutes=2))
        self.authenticate(**bearer(self.key))
        self.assertGreater(ApiToken.objects.get().last_used_at, first_use - timedelta(minutes=2))

    def test_get_bearer_key_strips_whitespace(self):
        self.assertEqual(get_bearer_key(self.factory.get("/", HTTP_AUTHORIZATION="Bearer  abc ")), "abc")


@token_required()
def plain_view(request):
    return HttpResponse(request.user.username)


@token_required("auth.view_user")
def plain_view_with_permission(request):
    return HttpResponse(request.user.username)


class TokenRequiredTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="client")
        _token, self.key = create_token(self.user)
        self.factory = RequestFactory()

    def test_responds_401_without_valid_token(self):
        response = plain_view(self.factory.get("/"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")

    def test_sets_request_user(self):
        response = plain_view(self.factory.get("/", **bearer(self.key)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"client")

    def test_responds_403_without_permission(self):
        response = plain_view_with_permission(self.factory.get("/", **bearer(self.key)))
        self.assertEqual(response.status_code, 403)

    def test_allows_user_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        response = plain_view_with_permission(self.factory.get("/", **bearer(self.key)))
        self.assertEqual(response.status_code, 200)


class DrfView(APIView):
    authentication_classes = (ApiTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({"user": request.user.username, "token": request.auth.name})


class DrfViewWithPermission(DrfView):
    permission_classes = (HasPerm("auth.view_user"),)


class LegacyHeaderAuthentication(ApiTokenAuthentication):
    def get_key(self, request):
        return super().get_key(request) or request.headers.get("X-Auth-Token")


class LegacyHeaderView(DrfView):
    authentication_classes = (LegacyHeaderAuthentication,)


class ApiTokenAuthenticationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="client")
        _token, self.key = create_token(self.user)
        self.factory = APIRequestFactory()

    def test_authenticates_user_and_sets_token_as_auth(self):
        response = DrfView.as_view()(self.factory.get("/", **bearer(self.key)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"user": "client", "token": "test"})

    def test_responds_401_with_bearer_challenge_without_key(self):
        response = DrfView.as_view()(self.factory.get("/"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")

    def test_responds_401_for_invalid_key(self):
        response = DrfView.as_view()(self.factory.get("/", **bearer("wrong")))
        self.assertEqual(response.status_code, 401)

    def test_has_perm(self):
        request = self.factory.get("/", **bearer(self.key))
        self.assertEqual(DrfViewWithPermission.as_view()(request).status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(codename="view_user"))
        request = self.factory.get("/", **bearer(self.key))
        self.assertEqual(DrfViewWithPermission.as_view()(request).status_code, 200)

    def test_subclass_can_read_key_from_legacy_header(self):
        response = LegacyHeaderView.as_view()(self.factory.get("/", HTTP_X_AUTH_TOKEN=self.key))
        self.assertEqual(response.status_code, 200)


class OpenApiSchemaTestCase(TestCase):
    def test_documents_bearer_scheme(self):
        pytest.importorskip("drf_spectacular")
        from drf_spectacular.extensions import OpenApiAuthenticationExtension

        extension = OpenApiAuthenticationExtension.get_match(ApiTokenAuthentication())
        self.assertEqual(extension.get_security_definition(None), {"type": "http", "scheme": "bearer"})


class ApiTokenAdminTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="pw")
        self.client.force_login(self.admin)
        self.client_user = User.objects.create(username="client")

    def test_shows_key_once_after_creation(self):
        response = self.client.post(
            reverse("admin:apitokens_apitoken_add"), {"user": self.client_user.pk, "name": "client secret"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        key = response.context["key"]
        self.assertContains(response, key)
        token = ApiToken.objects.get()
        self.assertEqual(token.user, self.client_user)
        self.assertEqual(token.key_hash, hash_key(key))

        response = self.client.get(reverse("admin:apitokens_apitoken_change", args=(token.pk,)))
        self.assertNotContains(response, key)
        self.assertNotContains(response, token.key_hash)

    @override_settings(BAUMBELT_API_TOKEN_PREFIX="")
    def test_shows_error_without_key_prefix_setting(self):
        response = self.client.post(
            reverse("admin:apitokens_apitoken_add"), {"user": self.client_user.pk, "name": "client secret"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set BAUMBELT_API_TOKEN_PREFIX")
        self.assertFalse(ApiToken.objects.exists())

    def test_user_is_read_only_after_creation(self):
        token, _key = create_token(self.client_user)
        other_user = User.objects.create(username="other")

        self.client.post(
            reverse("admin:apitokens_apitoken_change", args=(token.pk,)), {"user": other_user.pk, "name": "renamed"}
        )

        token.refresh_from_db()
        self.assertEqual(token.name, "renamed")
        self.assertEqual(token.user, self.client_user)


class CreateApiTokenCommandTestCase(TestCase):
    def test_prints_key_of_new_token(self):
        user = User.objects.create(username="client")
        stdout = StringIO()

        call_command("create-api-token", "client", "client secret", "--expires-at", "2030-01-31", stdout=stdout)

        key = stdout.getvalue().strip()
        token = ApiToken.objects.get(key_hash=hash_key(key))
        self.assertEqual((token.user, token.name), (user, "client secret"))
        self.assertEqual(timezone.localtime(token.expires_at).date().isoformat(), "2030-01-31")

    @override_settings(BAUMBELT_API_TOKEN_PREFIX="")
    def test_fails_without_key_prefix_setting(self):
        User.objects.create(username="client")
        with self.assertRaisesMessage(CommandError, "Set BAUMBELT_API_TOKEN_PREFIX"):
            call_command("create-api-token", "client", "secret", stdout=StringIO())
        self.assertFalse(ApiToken.objects.exists())

    def test_fails_for_unknown_user(self):
        with self.assertRaises(CommandError):
            call_command("create-api-token", "nobody", "secret", stdout=StringIO())
