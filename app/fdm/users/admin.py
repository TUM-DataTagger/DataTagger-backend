from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group as DjangoGroup
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from fdm.users.models import Group

User = get_user_model()

admin.site.unregister(DjangoGroup)

__all__ = [
    "MyUserChangeForm",
    "MyUserCreationForm",
    "MyUserAdmin",
]


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(UserCreationForm):
    error_message = UserCreationForm.error_messages.update(
        {
            "duplicate_username": "This username has already been taken.",
        },
    )

    class Meta(UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise forms.ValidationError(self.error_messages["duplicate_username"])


@admin.register(User)
class MyUserAdmin(AuthUserAdmin):
    form = MyUserChangeForm

    add_form = MyUserCreationForm

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "password",
                ),
            },
        ),
        (
            _(
                "Personal info",
            ),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "can_hard_delete_datasets",
                    "is_global_metadata_template_admin",
                    "is_global_approval_queue_admin",
                ),
            },
        ),
        (
            _("Create Projects Permission (Automatically synced for shibboleth users)"),
            {
                "fields": ("can_create_projects",),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                ),
            },
        ),
        (
            _("Shibboleth Attributes"),
            {
                "fields": (
                    "given_name",
                    "sn",
                    "edu_person_affiliation",
                    "im_org_zug_mitarbeiter",
                    "im_org_zug_gast",
                    "im_org_zug_student",
                    "im_akademischer_grad",
                    "im_titel_anrede",
                    "im_titel_pre",
                    "im_titel_post",
                ),
            },
        ),
    )

    list_display = [
        "username",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_anonymized",
        "can_create_projects",
        "is_global_metadata_template_admin",
        "is_global_approval_queue_admin",
    ]

    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "is_anonymized",
        "can_create_projects",
        "can_hard_delete_datasets",
        "is_global_metadata_template_admin",
        "is_global_approval_queue_admin",
    ]

    search_fields = [
        "pk",
        "username",
        "first_name",
        "last_name",
        "email",
        "given_name",
        "sn",
        "edu_person_affiliation",
        "im_org_zug_mitarbeiter",
        "im_org_zug_gast",
        "im_org_zug_student",
        "im_akademischer_grad",
        "im_titel_anrede",
        "im_titel_pre",
        "im_titel_post",
    ]

    readonly_fields = [
        "date_joined",
        "last_login",
        "authentication_provider",
        "given_name",
        "sn",
        "edu_person_affiliation",
        "im_org_zug_mitarbeiter",
        "im_org_zug_gast",
        "im_org_zug_student",
        "im_akademischer_grad",
        "im_titel_anrede",
        "im_titel_pre",
        "im_titel_post",
    ]

    actions = [
        "anonymize_selected_users",
    ]

    add_fieldsets = (
        (
            None,
            {
                "classes": [
                    "wide",
                ],
                "fields": [
                    "first_name",
                    "last_name",
                    "username",
                    "email",
                    "password1",
                    "password2",
                ],
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def anonymize_selected_users(self, request, queryset):
        backlink = request.get_full_path()

        if "apply" in request.POST:
            users_count = queryset.count()

            try:
                for user in queryset.all():
                    user.anonymize()

                if users_count == 1:
                    message = _("{user} has been anonymized").format(
                        user=queryset.first(),
                    )
                else:
                    message = _("{users_count} users have been anonymized").format(
                        users_count=users_count,
                    )

                self.message_user(
                    request,
                    message,
                    level=messages.SUCCESS,
                )
            except Exception as e:
                if users_count == 1:
                    message = _("{user} could not be anonymized: {error}").format(
                        user=queryset.first(),
                        error=e,
                    )
                else:
                    message = _("{users_count} users could not be anonymized: {error}").format(
                        users_count=users_count,
                        error=e,
                    )

                self.message_user(
                    request,
                    message,
                    level=messages.ERROR,
                )

            return HttpResponseRedirect(backlink)

        context = self.admin_site.each_context(request)
        context["opts"] = self.model._meta
        context["selected_users"] = queryset.all()
        context["backlink"] = backlink

        return render(
            request,
            "users/admin/anonymize_user.html",
            context=context,
        )

    anonymize_selected_users.short_description = _("Anonymize selected users")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if object_id is not None:
            extra_context = extra_context or {}
            extra_context["anonymize_button"] = True

        return super().changeform_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        if "_anonymize" in request.POST:
            queryset = self.get_queryset(request).filter(pk=obj.pk)

            return self.anonymize_selected_users(request, queryset)
        else:
            return super().response_change(request, obj)


@admin.register(Group)
class MyGroupAdmin(GroupAdmin):
    list_display = [
        "name",
    ]

    search_fields = [
        "name",
    ]

    fields = [
        "name",
        "permissions",
    ]

    readonly_fields = [
        "name",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Disable Group admin for now, reenable if needed
admin.site.unregister(Group)
