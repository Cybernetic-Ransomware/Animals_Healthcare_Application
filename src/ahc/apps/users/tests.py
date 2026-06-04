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
