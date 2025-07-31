from django.urls import reverse

from rest_framework import status

import pytest


@pytest.mark.django_db
class TestUserAPI:
    def test_read_current_user_details(self, client, initial_users):
        """
        Ensure we can read the user details of the currently logged-in user.
        """
        url = reverse("user-me")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == initial_users["user_1"].username
        assert response.data["email"] == initial_users["user_1"].email

    def test_user_list_is_empty(self, client, initial_users):
        """
        Ensure the user list is empty.
        """
        url = reverse("user-list")

        response = client.get(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
