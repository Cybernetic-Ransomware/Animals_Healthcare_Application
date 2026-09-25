import pytest

from ahc.apps.animals.models import Animal


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalTabView:
    """AnimalTabView: htmx vs full-page response, access control."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Luna", owner=profile)

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_htmx_request_returns_fragment_without_base_title(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        url = f"/pet/{animal.id}/tab/mainpage/"
        response = c.get(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<title>" not in content

    def test_non_htmx_request_returns_full_page_with_base_title(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        url = f"/pet/{animal.id}/tab/mainpage/"
        response = c.get(url)
        assert response.status_code == 200
        assert "<title>" in response.content.decode()

    def test_all_public_slugs_return_200_for_owner(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        for slug in ("mainpage", "vet", "diet", "notes", "ownership", "settings"):
            url = f"/pet/{animal.id}/tab/{slug}/"
            response = c.get(url, HTTP_HX_REQUEST="true")
            assert response.status_code == 200, f"Expected 200 for slug={slug!r}, got {response.status_code}"

    def test_owner_only_tabs_return_403_for_keeper(self, animal, second_user_profile):
        other_user, other_profile = second_user_profile
        animal.allowed_users.add(other_profile)
        c = self._client_for(other_user)
        for slug in ("ownership", "settings"):
            url = f"/pet/{animal.id}/tab/{slug}/"
            response = c.get(url, HTTP_HX_REQUEST="true")
            assert response.status_code == 403, f"Expected 403 for keeper on slug={slug!r}, got {response.status_code}"

    def test_non_accessible_user_gets_403(self, animal, second_user_profile):
        other_user, _ = second_user_profile
        c = self._client_for(other_user)
        url = f"/pet/{animal.id}/tab/mainpage/"
        response = c.get(url)
        assert response.status_code == 403

    def test_unknown_slug_returns_404(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        url = f"/pet/{animal.id}/tab/nonexistent/"
        response = c.get(url)
        assert response.status_code == 404
