from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import (
    animals_for_biometric_batch,
    animals_visible_to,
    deceased_animals_for,
    is_animal_owner,
    is_pinned,
    recent_records_for,
    user_can_access_animal,
    user_can_modify_animal,
    user_can_record_biometrics,
    user_can_view_animal,
)


@pytest.mark.unit
class TestIsAnimalOwnerSelector:
    """is_animal_owner: pure predicate — no DB; uses MagicMock."""

    def test_returns_true_for_owner(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = profile
        assert is_animal_owner(profile, animal) is True

    def test_returns_false_for_non_owner(self):
        owner = MagicMock()
        other = MagicMock()
        animal = MagicMock()
        animal.owner = owner
        assert is_animal_owner(other, animal) is False


@pytest.mark.unit
class TestUserCanAccessAnimalSelector:
    """user_can_access_animal: short-circuits on owner; delegates to active_share_for otherwise."""

    def test_owner_can_access(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = profile
        with patch("ahc.apps.animals.selectors.active_share_for") as mock_share:
            assert user_can_access_animal(profile, animal) is True
            mock_share.assert_not_called()

    def test_keeper_can_access(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = MagicMock()
        animal.date_of_death = None  # living animal — carer access applies
        with patch("ahc.apps.animals.selectors.active_share_for", return_value=MagicMock()):
            assert user_can_access_animal(profile, animal) is True

    def test_stranger_cannot_access(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = MagicMock()
        animal.date_of_death = None  # living animal — no share
        with patch("ahc.apps.animals.selectors.active_share_for", return_value=None):
            assert user_can_access_animal(profile, animal) is False


@pytest.mark.unit
class TestIsPinnedSelector:
    """is_pinned: delegates to profile.pinned_animals.filter().exists()."""

    def test_pinned_returns_true(self):
        profile = MagicMock()
        animal = MagicMock()
        profile.pinned_animals.filter.return_value.exists.return_value = True
        assert is_pinned(profile, animal) is True
        profile.pinned_animals.filter.assert_called_once_with(pk=animal.pk)

    def test_not_pinned_returns_false(self):
        profile = MagicMock()
        animal = MagicMock()
        profile.pinned_animals.filter.return_value.exists.return_value = False
        assert is_pinned(profile, animal) is False


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalsVisibleToSelector:
    """animals_visible_to: ORM query — returns owner + keeper animals."""

    def test_owner_sees_own_animal(self, animal, user_profile):
        _, profile = user_profile
        assert animal in animals_visible_to(profile)

    def test_keeper_sees_allowed_animal(self, animal, second_user_profile):
        _, other_profile = second_user_profile
        animal.allowed_users.add(other_profile)
        assert animal in animals_visible_to(other_profile)

    def test_stranger_cannot_see_animal(self, animal, second_user_profile):
        _, other_profile = second_user_profile
        assert animal not in animals_visible_to(other_profile)


@pytest.mark.integration
@pytest.mark.django_db
class TestRecentRecordsForSelector:
    """recent_records_for: returns MedicalRecords for the animal, newest first."""

    def test_returns_empty_when_no_records(self, animal):
        records = list(recent_records_for(animal))
        assert records == []

    def test_respects_limit(self, animal, user_profile):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

        _, profile = user_profile
        for i in range(7):
            MedicalRecord.objects.create(
                animal=animal,
                author=profile,
                short_description=f"Note {i}",
                type_of_event="general",
            )
        records = list(recent_records_for(animal, limit=5))
        assert len(records) == 5


@pytest.mark.unit
class TestDeceasedPredicates:
    """user_can_view_animal / user_can_modify_animal behaviour on deceased animals."""

    def _make_animal(self, owner, deceased=False):
        animal = MagicMock(spec=Animal)
        animal.owner = owner
        animal.date_of_death = date(2024, 1, 1) if deceased else None
        return animal

    def test_owner_can_view_living_animal(self):
        profile = MagicMock()
        animal = self._make_animal(owner=profile, deceased=False)
        assert user_can_view_animal(profile, animal) is True

    def test_owner_can_view_deceased_animal(self):
        profile = MagicMock()
        animal = self._make_animal(owner=profile, deceased=True)
        assert user_can_view_animal(profile, animal) is True

    def test_owner_cannot_modify_deceased_animal(self):
        profile = MagicMock()
        animal = self._make_animal(owner=profile, deceased=True)
        assert user_can_modify_animal(profile, animal) is False

    def test_owner_can_modify_living_animal(self):
        profile = MagicMock()
        animal = self._make_animal(owner=profile, deceased=False)
        assert user_can_modify_animal(profile, animal) is True

    def test_carer_cannot_view_deceased_animal(self):
        profile = MagicMock()
        owner = MagicMock()
        animal = self._make_animal(owner=owner, deceased=True)
        assert user_can_view_animal(profile, animal) is False

    def test_carer_cannot_modify_deceased_animal(self):
        profile = MagicMock()
        owner = MagicMock()
        animal = self._make_animal(owner=owner, deceased=True)
        assert user_can_modify_animal(profile, animal) is False


@pytest.mark.integration
@pytest.mark.django_db
class TestDeceasedSelectors:
    """animals_visible_to / deceased_animals_for on deceased animals."""

    @pytest.fixture
    def deceased_animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15))

    def test_animals_visible_to_excludes_deceased_for_owner(self, deceased_animal, user_profile):
        _, profile = user_profile
        assert deceased_animal not in animals_visible_to(profile)

    def test_animals_visible_to_excludes_deceased_for_carer(self, deceased_animal, second_user_profile, user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=deceased_animal, carer=carer_profile)
        assert deceased_animal not in animals_visible_to(carer_profile)

    def test_deceased_animals_for_returns_owners_deceased(self, deceased_animal, user_profile):
        _, profile = user_profile
        assert deceased_animal in deceased_animals_for(profile)

    def test_deceased_animals_for_excludes_carers_deceased(self, deceased_animal, second_user_profile):
        _, other_profile = second_user_profile
        assert deceased_animal not in deceased_animals_for(other_profile)

    def test_deceased_animals_for_excludes_living(self, animal, user_profile):
        _, profile = user_profile
        assert animal not in deceased_animals_for(profile)


@pytest.mark.integration
@pytest.mark.django_db
class TestUserCanRecordBiometrics:
    """user_can_record_biometrics: biometric-category gate layered on top of modify access."""

    def test_owner_can_record_biometrics(self, animal, user_profile):
        _, profile = user_profile
        assert user_can_record_biometrics(profile, animal) is True

    def test_carer_with_allow_biometrics_can_record(self, animal, second_user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=True)
        assert user_can_record_biometrics(carer_profile, animal) is True

    def test_carer_without_allow_biometrics_blocked(self, animal, second_user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=False)
        assert user_can_record_biometrics(carer_profile, animal) is False

    def test_stranger_without_share_blocked(self, animal, second_user_profile):
        _, other_profile = second_user_profile
        assert user_can_record_biometrics(other_profile, animal) is False

    def test_deceased_animal_blocked_even_for_owner(self, user_profile):
        _, profile = user_profile
        deceased = Animal.objects.create(full_name="Gone", owner=profile, date_of_death=date(2024, 1, 1))
        assert user_can_record_biometrics(profile, deceased) is False


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalsForBiometricBatch:
    """animals_for_biometric_batch: owner always included; carer only with allow_biometrics."""

    def test_owner_animal_included(self, animal, user_profile):
        _, profile = user_profile
        assert animal in animals_for_biometric_batch(profile)

    def test_carer_with_allow_biometrics_included(self, animal, second_user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=True)
        assert animal in animals_for_biometric_batch(carer_profile)

    def test_carer_without_allow_biometrics_excluded(self, animal, second_user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=False)
        assert animal not in animals_for_biometric_batch(carer_profile)

    def test_expired_share_with_allow_biometrics_excluded(self, animal, second_user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=True, valid_until=date(2020, 1, 1))
        assert animal not in animals_for_biometric_batch(carer_profile)

    def test_deceased_animal_excluded_for_owner(self, user_profile):
        _, profile = user_profile
        deceased = Animal.objects.create(full_name="Gone", owner=profile, date_of_death=date(2024, 1, 1))
        assert deceased not in animals_for_biometric_batch(profile)
