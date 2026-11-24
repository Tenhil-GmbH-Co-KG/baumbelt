from django import forms
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse

from baumbelt.django.apitokens.models import ApiToken, get_key_prefix


class ApiTokenAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        if self.instance._state.adding:
            try:
                get_key_prefix()
            except ImproperlyConfigured as e:
                raise forms.ValidationError(str(e))
        return cleaned_data


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    form = ApiTokenAdminForm
    list_display = ("name", "user", "created_at", "expires_at", "last_used_at")
    list_select_related = ("user",)
    search_fields = ("name",)
    fields = ("user", "name", "expires_at", "created_at", "last_used_at")
    readonly_fields = ("created_at", "last_used_at")
    # a select of all users is too big in services that have a User per visitor
    raw_id_fields = ("user",)

    def get_readonly_fields(self, request, obj=None):
        # to move a token to another user, create a new one instead
        return (*self.readonly_fields, "user") if obj else self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:
            obj._new_key = obj.set_new_key()
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        # The key is rendered directly instead of as a message. Messages may be stored in a cookie.
        key = getattr(obj, "_new_key", None)
        if key is None:
            return super().response_add(request, obj, post_url_continue)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": "New API token",
            "token": obj,
            "key": key,
        }
        return TemplateResponse(request, "admin/apitokens/apitoken/new_key.html", context)


class ApiTokenInline(admin.TabularInline):
    """Lists the tokens of a user. Add it to the admin of the User model."""

    model = ApiToken
    fields = ("name", "created_at", "expires_at", "last_used_at")
    readonly_fields = fields
    extra = 0
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        # created in the API token admin, which shows the key once
        return False
