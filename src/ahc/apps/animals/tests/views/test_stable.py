from datetime import date

import pytest

from ahc.apps.animals.models import Animal


@pytest.mark.integration
@pytest.mark.django_db
class TestStableView:
    """StableView: animal list page for authenticated users."""

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_unauthenticated_redirects_to_login(self):
        from django.test import Client

        response = Client().get("/pet/animals/")
        assert response.status_code == 302

    def test_owner_sees_own_animal_in_context(self, user_profile):
        user, profile = user_profile
        animal = Animal.objects.create(full_name="StableAnimal", owner=profile)
        response = self._client_for(user).get("/pet/animals/")
        assert response.status_code == 200
        assert animal in response.context["animals"]

    def test_card_uses_static_fallback_when_no_custom_image(self, user_profile):
        user, profile = user_profile
        animal = Animal.objects.create(full_name="StableAnimal", owner=profile)
        assert animal.profile_image.name == ""
        response = self._client_for(user).get("/pet/animals/")
        assert "img/defaults/pet-care.png" in response.content.decode()


@pytest.mark.integration
@pytest.mark.django_db
class TestToPinAnimalsView:
    """ToPinAnimalsView: JSON pin/unpin endpoint with access control."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="PinMe", owner=profile)

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_post_pin_returns_success_json(self, animal, user_profile):
        import json

        user, _ = user_profile
        response = self._client_for(user).post("/pet/pinned-animals/", {"animal_id": str(animal.id), "action": "add"})
        assert response.status_code == 200
        assert json.loads(response.content)["status"] == "success"

    def test_post_unpin_returns_success_json(self, animal, user_profile):
        import json

        user, profile = user_profile
        profile.pinned_animals.add(animal)
        response = self._client_for(user).post("/pet/pinned-animals/", {"animal_id": str(animal.id), "action": "remove"})
        assert response.status_code == 200
        assert json.loads(response.content)["status"] == "success"

    def test_pin_with_no_access_returns_403_json(self, animal, second_user_profile):
        import json

        other_user, _ = second_user_profile
        response = self._client_for(other_user).post("/pet/pinned-animals/", {"animal_id": str(animal.id), "action": "add"})
        assert response.status_code == 403
        assert json.loads(response.content)["status"] == "forbidden"


@pytest.mark.integration
@pytest.mark.django_db
class TestStableAndArchiveViews:
    """StableView excludes deceased; ArchiveView shows only owner's deceased."""

    @pytest.fixture
    def deceased_animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15))

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_stable_view_excludes_deceased(self, animal, deceased_animal, user_profile):
        user, _ = user_profile
        response = self._client_for(user).get("/pet/animals/")
        assert response.status_code == 200
        assert animal in response.context["animals"]
        assert deceased_animal not in response.context["animals"]

    def test_archive_view_includes_deceased(self, deceased_animal, user_profile):
        user, _ = user_profile
        response = self._client_for(user).get("/pet/archive/")
        assert response.status_code == 200
        assert deceased_animal in response.context["animals"]

    def test_archive_view_excludes_living(self, animal, user_profile):
        user, _ = user_profile
        response = self._client_for(user).get("/pet/archive/")
        assert animal not in response.context["animals"]

    def test_archive_view_excludes_other_owners_deceased(self, deceased_animal, second_user_profile):
        other_user, _ = second_user_profile
        response = self._client_for(other_user).get("/pet/archive/")
        assert deceased_animal not in response.context["animals"]
