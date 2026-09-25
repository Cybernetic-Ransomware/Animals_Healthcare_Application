from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.integration
@pytest.mark.django_db
class TestUserRegisterView:
    """UserRegisterView: form rendering and user account creation."""

    def test_get_renders_registration_form(self):
        from django.test import Client

        response = Client().get("/user/register/")
        assert response.status_code == 200

    def test_valid_post_creates_user_and_redirects_to_login(self):
        from django.contrib.auth.models import User
        from django.test import Client

        mock_img = MagicMock()
        mock_img.height = 100
        mock_img.width = 100
        with patch("ahc.apps.users.models.Image.open", return_value=mock_img):
            response = Client().post(
                "/user/register/",
                {
                    "username": "brandnewuser",
                    "email": "newuser@example.com",
                    "password1": "test-fixture-password-1",
                    "password2": "test-fixture-password-1",
                },
            )
        assert response.status_code == 302
        assert User.objects.filter(username="brandnewuser").exists()

    def test_invalid_post_re_renders_form_with_errors(self):
        from django.test import Client

        response = Client().post(
            "/user/register/",
            {"username": "u", "email": "not-an-email", "password1": "abc", "password2": "xyz"},
        )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestUserProfileView:
    """UserProfileView: authenticated profile editing."""

    @pytest.fixture(autouse=True)
    def _media_root(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "profile_pics" / "users").mkdir(parents=True)

    def test_unauthenticated_redirects_to_login(self):
        from django.test import Client

        response = Client().get("/user/profile/")
        assert response.status_code == 302

    def test_authenticated_get_returns_200(self, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get("/user/profile/")
        assert response.status_code == 200

    def test_get_renders_user_and_profile_form_fields(self, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get("/user/profile/")
        content = response.content.decode()
        assert 'name="username"' in content
        assert 'name="email"' in content
        assert 'name="profile_image"' in content
        assert 'enctype="multipart/form-data"' in content

    def test_get_uses_static_fallback_when_no_custom_image(self, user_profile, logged_in_client):
        user, profile = user_profile
        assert profile.profile_image.name == ""
        response = logged_in_client(user).get("/user/profile/")
        assert "img/defaults/signup2.png" in response.content.decode()

    def test_valid_post_updates_username_and_redirects(self, user_profile, logged_in_client):
        user, _ = user_profile
        mock_img = MagicMock()
        mock_img.height = 100
        mock_img.width = 100
        with patch("ahc.apps.users.models.Image.open", return_value=mock_img):
            response = logged_in_client(user).post(
                "/user/profile/", {"username": "updatedname", "email": "updated@example.com"}
            )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.username == "updatedname"

    def test_valid_post_with_image_saves_profile_image(self, user_profile, logged_in_client, png_upload):
        user, profile = user_profile
        response = logged_in_client(user).post(
            "/user/profile/",
            {"username": "updatedname", "email": "updated@example.com", "profile_image": png_upload()},
        )
        assert response.status_code == 302
        profile.refresh_from_db()
        assert profile.profile_image.name != ""
        assert profile.profile_image.name.startswith("profile_pics/users/")

    def test_custom_image_rendered_after_upload(self, user_profile, logged_in_client, png_upload):
        user, profile = user_profile
        logged_in_client(user).post(
            "/user/profile/",
            {"username": user.username, "email": "updated2@example.com", "profile_image": png_upload()},
        )
        profile.refresh_from_db()

        response = logged_in_client(user).get("/user/profile/")
        content = response.content.decode()
        assert profile.profile_image.url in content
        assert "img/defaults/signup2.png" not in content

    def test_post_without_new_file_keeps_existing_custom_image(self, user_profile, logged_in_client):
        user, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        existing_name = profile.profile_image.name

        response = logged_in_client(user).post(
            "/user/profile/", {"username": "renamedonly", "email": "renamed@example.com"}
        )
        assert response.status_code == 302
        profile.refresh_from_db()
        assert profile.profile_image.name == existing_name

    def test_invalid_user_form_does_not_save_profile(self, user_profile, logged_in_client, png_upload):
        user, profile = user_profile
        response = logged_in_client(user).post(
            "/user/profile/",
            {"username": "", "email": "updated@example.com", "profile_image": png_upload()},
        )
        assert response.status_code == 200
        profile.refresh_from_db()
        assert profile.profile_image.name == ""

    def test_invalid_profile_image_does_not_save_user(self, user_profile, logged_in_client):
        user, _ = user_profile
        bad_file = SimpleUploadedFile("not-an-image.png", b"not-an-image-bytes", content_type="image/png")
        response = logged_in_client(user).post(
            "/user/profile/",
            {"username": "shouldnotchange", "email": "updated@example.com", "profile_image": bad_file},
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.username != "shouldnotchange"


@pytest.mark.integration
@pytest.mark.django_db
class TestShareDefaultsView:
    """ShareDefaultsView: default share scope configuration for new keepers."""

    def test_unauthenticated_redirects_to_login(self):
        from django.test import Client

        response = Client().get("/user/share-defaults/")
        assert response.status_code == 302

    def test_authenticated_get_returns_200(self, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get("/user/share-defaults/")
        assert response.status_code == 200

    def test_valid_post_saves_defaults_and_redirects(self, user_profile, logged_in_client):
        from ahc.apps.animals.models import ShareDefaults

        user, profile = user_profile
        response = logged_in_client(user).post("/user/share-defaults/", {"allow_basic": "on", "allow_diet": "on"})
        assert response.status_code == 302
        defaults = ShareDefaults.objects.get(profile=profile)
        assert defaults.allow_basic is True
        assert defaults.allow_diet is True
        assert defaults.allow_vet_contact is False
