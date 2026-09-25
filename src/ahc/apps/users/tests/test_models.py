import pytest

from ahc.apps.users.models import Profile


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
