from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from PIL import Image as PILImage

from ahc.apps.users.models import Profile
from ahc.apps.users.signals import create_background, create_basic_privilege


def _valid_png_upload(name: str = "avatar.png") -> SimpleUploadedFile:
    """A real, minimal, Pillow-decodable PNG — Django's ImageField validates actual image content."""
    buf = BytesIO()
    PILImage.new("RGB", (10, 10), color="red").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


@pytest.mark.integration
@pytest.mark.django_db
class TestProfileModel:
    def test_str_returns_username(self, user_profile):
        _, profile = user_profile
        assert str(profile) == "testuser"

    def test_profile_linked_to_user(self, user_profile):
        user, profile = user_profile
        assert profile.user == user

    def test_allow_recent_animals_list_defaults_to_true(self, user_profile):
        _, profile = user_profile
        assert profile.allow_recennt_animals_list is True

    def test_pinned_animals_empty_by_default(self, user_profile):
        _, profile = user_profile
        assert profile.pinned_animals.count() == 0

    def test_profile_is_unique_per_user(self, user_profile):
        user, _ = user_profile
        assert Profile.objects.filter(user=user).count() == 1

    def test_profile_has_privilege_tier_after_creation(self, user_profile):
        _, profile = user_profile
        assert profile.privilege_tier is not None
        assert profile.privilege_tier.title == "Empty Privilege"

    def test_profile_has_background_after_creation(self, user_profile):
        _, profile = user_profile
        assert profile.profile_background is not None
        assert profile.profile_background.title == "Default Background"


@pytest.mark.integration
@pytest.mark.django_db
class TestRemoveOldPicturesAfterProfileDeleteSignal:
    """remove_old_pictures_after_profile_delete: transaction-safe targeted delete."""

    @pytest.fixture(autouse=True)
    def _media_root(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "profile_pics" / "users").mkdir(parents=True)

    def test_custom_image_removed_after_commit(self, django_capture_on_commit_callbacks, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(profile.profile_image.path)
        assert image_path.exists()

        with django_capture_on_commit_callbacks(execute=True):
            profile.delete()

        assert not image_path.exists()

    def test_blank_image_delete_does_not_unlink_files(self, django_capture_on_commit_callbacks, user_profile, tmp_path):
        _, profile = user_profile
        assert profile.profile_image.name == ""

        # Proves the guard short-circuits on the blank name before touching disk at all.
        sentinel = tmp_path / "profile_pics" / "users" / "sentinel.png"
        sentinel.write_bytes(b"unrelated-file-bytes")

        with (
            patch.object(Path, "unlink") as mock_unlink,
            django_capture_on_commit_callbacks(execute=True),
        ):
            profile.delete()

        mock_unlink.assert_not_called()
        assert sentinel.exists()

    def test_missing_file_on_disk_does_not_raise(self, django_capture_on_commit_callbacks, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        Path(profile.profile_image.path).unlink()

        with django_capture_on_commit_callbacks(execute=True):
            profile.delete()

    def test_callback_failure_does_not_propagate_and_record_stays_deleted(
        self, django_capture_on_commit_callbacks, user_profile
    ):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        profile_id = profile.id

        with (
            patch.object(Path, "unlink", side_effect=PermissionError("simulated")),
            django_capture_on_commit_callbacks(execute=True),
        ):
            profile.delete()

        assert not Profile.objects.filter(id=profile_id).exists()

    def test_user_delete_cascade_removes_profile_image(self, django_capture_on_commit_callbacks, user_profile):
        user, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(profile.profile_image.path)
        assert image_path.exists()

        with django_capture_on_commit_callbacks(execute=True):
            user.delete()

        assert not image_path.exists()
        assert not Profile.objects.filter(pk=profile.pk).exists()

    def test_rollback_keeps_record_and_file(self, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(profile.profile_image.path)
        profile_id = profile.id

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom), transaction.atomic():
            profile.delete()
            raise _Boom()

        assert Profile.objects.filter(id=profile_id).exists()
        assert image_path.exists()


@pytest.mark.unit
class TestCreateBasicPrivilegeSignal:
    """create_basic_privilege: assigns Empty Privilege when profile has none."""

    def test_assigns_privilege_when_missing(self):
        privilege_mock = MagicMock()
        instance = MagicMock(spec=Profile)
        instance.privilege_tier = None

        with patch("ahc.apps.users.signals.Privilege.objects.get_or_create", return_value=(privilege_mock, True)):
            create_basic_privilege(sender=Profile, instance=instance)

        assert instance.privilege_tier is privilege_mock

    def test_skips_when_privilege_already_set(self):
        instance = MagicMock(spec=Profile)
        instance.privilege_tier = MagicMock()

        with patch("ahc.apps.users.signals.Privilege.objects.get_or_create") as mock_goc:
            create_basic_privilege(sender=Profile, instance=instance)

        mock_goc.assert_not_called()


@pytest.mark.unit
class TestCreateBackgroundSignal:
    """create_background: assigns Default Background when profile has none."""

    def test_assigns_background_when_missing(self):
        background_mock = MagicMock()
        instance = MagicMock(spec=Profile)
        instance.profile_background = None

        with patch("ahc.apps.users.signals.ProfileBackground.objects.get_or_create", return_value=(background_mock, True)):
            create_background(sender=Profile, instance=instance)

        assert instance.profile_background is background_mock

    def test_skips_when_background_already_set(self):
        instance = MagicMock(spec=Profile)
        instance.profile_background = MagicMock()

        with patch("ahc.apps.users.signals.ProfileBackground.objects.get_or_create") as mock_goc:
            create_background(sender=Profile, instance=instance)

        mock_goc.assert_not_called()


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

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_unauthenticated_redirects_to_login(self):
        from django.test import Client

        response = Client().get("/user/profile/")
        assert response.status_code == 302

    def test_authenticated_get_returns_200(self, user_profile):
        user, _ = user_profile
        response = self._client_for(user).get("/user/profile/")
        assert response.status_code == 200

    def test_get_renders_user_and_profile_form_fields(self, user_profile):
        user, _ = user_profile
        response = self._client_for(user).get("/user/profile/")
        content = response.content.decode()
        assert 'name="username"' in content
        assert 'name="email"' in content
        assert 'name="profile_image"' in content
        assert 'enctype="multipart/form-data"' in content

    def test_get_uses_static_fallback_when_no_custom_image(self, user_profile):
        user, profile = user_profile
        assert profile.profile_image.name == ""
        response = self._client_for(user).get("/user/profile/")
        assert "img/defaults/signup2.png" in response.content.decode()

    def test_valid_post_updates_username_and_redirects(self, user_profile):
        user, _ = user_profile
        mock_img = MagicMock()
        mock_img.height = 100
        mock_img.width = 100
        with patch("ahc.apps.users.models.Image.open", return_value=mock_img):
            response = self._client_for(user).post(
                "/user/profile/", {"username": "updatedname", "email": "updated@example.com"}
            )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.username == "updatedname"

    def test_valid_post_with_image_saves_profile_image(self, user_profile):
        user, profile = user_profile
        response = self._client_for(user).post(
            "/user/profile/",
            {"username": "updatedname", "email": "updated@example.com", "profile_image": _valid_png_upload()},
        )
        assert response.status_code == 302
        profile.refresh_from_db()
        assert profile.profile_image.name != ""
        assert profile.profile_image.name.startswith("profile_pics/users/")

    def test_custom_image_rendered_after_upload(self, user_profile):
        user, profile = user_profile
        self._client_for(user).post(
            "/user/profile/",
            {"username": user.username, "email": "updated2@example.com", "profile_image": _valid_png_upload()},
        )
        profile.refresh_from_db()

        response = self._client_for(user).get("/user/profile/")
        content = response.content.decode()
        assert profile.profile_image.url in content
        assert "img/defaults/signup2.png" not in content

    def test_post_without_new_file_keeps_existing_custom_image(self, user_profile):
        user, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        existing_name = profile.profile_image.name

        response = self._client_for(user).post(
            "/user/profile/", {"username": "renamedonly", "email": "renamed@example.com"}
        )
        assert response.status_code == 302
        profile.refresh_from_db()
        assert profile.profile_image.name == existing_name

    def test_invalid_user_form_does_not_save_profile(self, user_profile):
        user, profile = user_profile
        response = self._client_for(user).post(
            "/user/profile/",
            {"username": "", "email": "updated@example.com", "profile_image": _valid_png_upload()},
        )
        assert response.status_code == 200
        profile.refresh_from_db()
        assert profile.profile_image.name == ""

    def test_invalid_profile_image_does_not_save_user(self, user_profile):
        user, _ = user_profile
        bad_file = SimpleUploadedFile("not-an-image.png", b"not-an-image-bytes", content_type="image/png")
        response = self._client_for(user).post(
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

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_unauthenticated_redirects_to_login(self):
        from django.test import Client

        response = Client().get("/user/share-defaults/")
        assert response.status_code == 302

    def test_authenticated_get_returns_200(self, user_profile):
        user, _ = user_profile
        response = self._client_for(user).get("/user/share-defaults/")
        assert response.status_code == 200

    def test_valid_post_saves_defaults_and_redirects(self, user_profile):
        from ahc.apps.animals.models import ShareDefaults

        user, profile = user_profile
        response = self._client_for(user).post("/user/share-defaults/", {"allow_basic": "on", "allow_diet": "on"})
        assert response.status_code == 302
        defaults = ShareDefaults.objects.get(profile=profile)
        assert defaults.allow_basic is True
        assert defaults.allow_diet is True
        assert defaults.allow_vet_contact is False
