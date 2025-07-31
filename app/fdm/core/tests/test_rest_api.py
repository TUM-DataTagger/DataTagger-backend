from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status

import pytest
from django_rest_passwordreset.models import ResetPasswordToken

from fdm.dbsettings.functions import set_dbsettings_value

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationAPI:
    def test_login_with_email_address(self, client, initial_users):
        """
        Ensure we can log in with a user's email address.
        """
        url = reverse("auth-list")

        response = client.post(
            url,
            {
                User.USERNAME_FIELD: initial_users["user_1"].email,
                "password": "password",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_login_with_uppercase_email_address(self, client, initial_users):
        """
        Ensure we can log in with a user's email address and capitalization doesn't matter.
        """
        url = reverse("auth-list")

        response = client.post(
            url,
            {
                User.USERNAME_FIELD: initial_users["user_1"].email.upper(),
                "password": "password",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_login_with_username(self, client, initial_users):
        """
        Ensure we can't log in with a user's username.
        """
        url = reverse("auth-list")

        response = client.post(
            url,
            {
                "username": initial_users["user_1"].username,
                "password": "password",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_with_different_authentication_provider(self, client):
        """
        Ensure we can't log in when a user account is connected to a different authentication provider.
        """
        url = reverse("auth-list")

        shibboleth_user = User.objects.create_user("shibboleth_user", "shibboleth_user@test.local", "password")
        shibboleth_user.authentication_provider = User.AuthenticationProvider.SHIBBOLETH
        shibboleth_user.is_active = True
        shibboleth_user.save()

        response = client.post(
            url,
            {
                User.USERNAME_FIELD: shibboleth_user.email,
                "password": "password",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_login_with_internal_email_address_tld(self, client):
        """
        Ensure we can't log in when a user's email address has an internal TLD.
        """
        url = reverse("auth-list")

        set_dbsettings_value("INTERNAL_TLDS", "internal.domain")

        internal_user = User.objects.create_user("internal_user", "internal_user@internal.domain", "password")
        internal_user.is_active = True
        internal_user.save()

        response = client.post(
            url,
            {
                User.USERNAME_FIELD: internal_user.email,
                "password": "password",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reset_password(self, client, initial_users):
        """
        Ensure we can request a password reset.
        """
        url = reverse("reset-password-request")

        client.post(
            url,
            {
                User.USERNAME_FIELD: initial_users["user_1"].email,
            },
            format="json",
        )

        assert ResetPasswordToken.objects.count() == 1

    def test_reset_password_with_internal_email_address_tld(self, client):
        """
        Ensure we can't request a password reset when a user's email address has an internal TLD.
        """
        url = reverse("reset-password-request")

        set_dbsettings_value("INTERNAL_TLDS", "internal.domain")

        internal_user = User.objects.create_user("internal_user", "internal_user@internal.domain", "password")
        internal_user.is_active = True
        internal_user.save()

        client.post(
            url,
            {
                User.USERNAME_FIELD: internal_user.email,
            },
            format="json",
        )

        assert ResetPasswordToken.objects.count() == 0
