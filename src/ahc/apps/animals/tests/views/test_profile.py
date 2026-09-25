import pytest
from django.core.files.base import ContentFile

from ahc.apps.animals.models import Animal


@pytest.mark.integration
@pytest.mark.django_db
class TestCreateAnimalView:
    """CreateAnimalView: form rendering, animal creation, and authentication gate."""

    def test_unauthenticated_redirects_to_login(self):
        from django.test import Client

        response = Client().get("/pet/create/")
        assert response.status_code == 302

    def test_get_renders_form(self, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get("/pet/create/")
        assert response.status_code == 200

    def test_valid_post_creates_animal_and_redirects_to_profile(self, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post("/pet/create/", {"full_name": "GoldenFish"})
        assert response.status_code == 302
        assert Animal.objects.filter(full_name="GoldenFish").exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalProfileDetailView:
    """AnimalProfileDetailView: full-page shell rendering and access control."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="ProfileTest", owner=profile)

    @pytest.fixture(autouse=True)
    def _media_root(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "profile_pics" / "animals").mkdir(parents=True)

    def test_unauthenticated_redirects_to_login(self, animal):
        from django.test import Client

        response = Client().get(f"/pet/{animal.id}/")
        assert response.status_code == 302

    def test_owner_gets_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/")
        assert response.status_code == 200

    def test_stranger_gets_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/")
        assert response.status_code == 403

    @pytest.mark.regression
    def test_uses_static_fallback_when_no_custom_image(self, animal, user_profile, logged_in_client):
        """Regression #58: the default animal image pointed at a missing media file."""
        user, _ = user_profile
        assert animal.profile_image.name == ""
        response = logged_in_client(user).get(f"/pet/{animal.id}/")
        assert "img/defaults/pet-care.png" in response.content.decode()

    def test_custom_image_used_instead_of_fallback(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        animal.profile_image.save("rex.png", ContentFile(b"fake-image-bytes"), save=True)
        response = logged_in_client(user).get(f"/pet/{animal.id}/")
        content = response.content.decode()
        assert animal.profile_image.url in content
        assert "img/defaults/pet-care.png" not in content


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalProfileViewDeceased:
    """AnimalProfileDetailView / AnimalTabView gate on deceased animals."""

    def test_owner_can_view_deceased_profile(self, deceased_animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{deceased_animal.id}/")
        assert response.status_code == 200

    def test_carer_blocked_on_deceased_profile(self, deceased_animal, second_user_profile, user_profile, logged_in_client):
        from ahc.apps.animals.models import AnimalShare

        other_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=deceased_animal, carer=carer_profile)
        response = logged_in_client(other_user).get(f"/pet/{deceased_animal.id}/")
        assert response.status_code == 403

    def test_owner_blocked_from_settings_tab_on_deceased(self, deceased_animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{deceased_animal.id}/tab/settings/")
        assert response.status_code == 403
