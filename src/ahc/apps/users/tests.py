from unittest.mock import MagicMock, patch

import pytest

from ahc.apps.users.models import Profile
from ahc.apps.users.signals import create_background, create_basic_privilege


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
                    "password1": "Str0ng_P@ssw0rd!",
                    "password2": "Str0ng_P@ssw0rd!",
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
