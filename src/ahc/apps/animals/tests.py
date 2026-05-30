from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import (
    animals_visible_to,
    is_animal_owner,
    is_pinned,
    recent_records_for,
    user_can_access_animal,
)
from ahc.apps.animals.services import (
    add_keeper,
    create_animal,
    pin_animal,
    process_profile_image,
    set_birthday,
    set_first_contact,
    transfer_ownership,
    unpin_animal,
)
from ahc.apps.animals.signals import update_allowed_users


@pytest.fixture
def animal(db, user_profile):
    _, profile = user_profile
    return Animal.objects.create(full_name="Whiskers", owner=profile)


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalModel:
    def test_animal_is_created_with_uuid_pk(self, animal):
        assert animal.id is not None
        assert animal.full_name == "Whiskers"

    def test_owner_is_assigned(self, animal, user_profile):
        _, profile = user_profile
        assert animal.owner == profile

    def test_no_keepers_by_default(self, animal):
        assert animal.allowed_users.count() == 0

    def test_second_user_can_be_added_as_keeper(self, animal, second_user_profile):
        _, other_profile = second_user_profile
        animal.allowed_users.add(other_profile)
        assert animal.allowed_users.filter(pk=other_profile.pk).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestUpdateAllowedUsersSignalHandler:
    """update_allowed_users: owner must not appear in allowed_users."""

    def test_owner_removed_when_present_in_allowed_users(self, animal, user_profile):
        _, profile = user_profile
        animal.allowed_users.add(profile)
        assert animal.allowed_users.filter(pk=profile.pk).exists()

        update_allowed_users(sender=Animal, instance=animal)

        assert not animal.allowed_users.filter(pk=profile.pk).exists()

    def test_non_owner_keeper_not_affected(self, animal, second_user_profile):
        _, other_profile = second_user_profile
        animal.allowed_users.add(other_profile)

        update_allowed_users(sender=Animal, instance=animal)

        assert animal.allowed_users.filter(pk=other_profile.pk).exists()

    def test_no_op_when_allowed_users_is_empty(self, animal):
        update_allowed_users(sender=Animal, instance=animal)
        assert animal.allowed_users.count() == 0


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
    """user_can_access_animal: short-circuits on owner; queries allowed_users otherwise."""

    def test_owner_can_access(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = profile
        assert user_can_access_animal(profile, animal) is True
        animal.allowed_users.filter.assert_not_called()

    def test_keeper_can_access(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = MagicMock()
        animal.allowed_users.filter.return_value.exists.return_value = True
        assert user_can_access_animal(profile, animal) is True
        animal.allowed_users.filter.assert_called_once_with(pk=profile.pk)

    def test_stranger_cannot_access(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = MagicMock()
        animal.allowed_users.filter.return_value.exists.return_value = False
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
class TestCreateAnimalService:
    """create_animal: assigns owner from profile, saves, and returns the new animal."""

    def test_assigns_owner_saves_and_returns(self):
        profile = MagicMock()
        form = MagicMock()
        animal_mock = MagicMock()
        form.save.return_value = animal_mock

        result = create_animal(profile, form)

        form.save.assert_called_once_with(commit=False)
        assert animal_mock.owner == profile
        animal_mock.save.assert_called_once()
        assert result is animal_mock


@pytest.mark.unit
class TestPinAnimalService:
    """pin_animal / unpin_animal: ownership-checked M2M operations on profile."""

    def test_pin_raises_when_no_access(self):
        profile = MagicMock()
        with (
            patch("ahc.apps.animals.services.get_object_or_404", return_value=MagicMock()),
            patch("ahc.apps.animals.services.user_can_access_animal", return_value=False),
            pytest.raises(PermissionError),
        ):
            pin_animal(profile, "some-uuid")

    def test_pin_adds_animal_when_access_granted(self):
        profile = MagicMock()
        animal = MagicMock()
        with (
            patch("ahc.apps.animals.services.get_object_or_404", return_value=animal),
            patch("ahc.apps.animals.services.user_can_access_animal", return_value=True),
        ):
            pin_animal(profile, "some-uuid")

        profile.pinned_animals.add.assert_called_once_with(animal)

    def test_unpin_removes_by_id(self):
        profile = MagicMock()
        unpin_animal(profile, "some-uuid")
        profile.pinned_animals.remove.assert_called_once_with("some-uuid")


@pytest.mark.unit
class TestProcessProfileImageService:
    """process_profile_image: thumbnail only when image exceeds 448x448."""

    def test_thumbnails_when_image_too_large(self):
        animal = MagicMock()
        img = MagicMock()
        img.height = 600
        img.width = 800
        with patch("ahc.apps.animals.services.Image.open", return_value=img):
            process_profile_image(animal)
        img.thumbnail.assert_called_once_with((448, 448))
        img.save.assert_called_once()

    def test_no_thumbnail_when_within_limit(self):
        animal = MagicMock()
        img = MagicMock()
        img.height = 200
        img.width = 200
        with patch("ahc.apps.animals.services.Image.open", return_value=img):
            process_profile_image(animal)
        img.thumbnail.assert_not_called()

    def test_thumbnail_when_exactly_one_dimension_exceeds(self):
        animal = MagicMock()
        img = MagicMock()
        img.height = 100
        img.width = 449
        with patch("ahc.apps.animals.services.Image.open", return_value=img):
            process_profile_image(animal)
        img.thumbnail.assert_called_once_with((448, 448))


@pytest.mark.unit
class TestTransferOwnershipService:
    """transfer_ownership: reassigns owner; optionally makes requester a keeper."""

    def test_assigns_new_owner_and_saves(self):
        animal = MagicMock()
        new_owner = MagicMock()
        requesting = MagicMock()

        transfer_ownership(animal, new_owner, set_keeper=False, requesting_profile=requesting)

        assert animal.owner == new_owner
        animal.save.assert_called_once()
        animal.allowed_users.add.assert_not_called()

    def test_adds_requesting_as_keeper_when_flag_is_set(self):
        animal = MagicMock()
        new_owner = MagicMock()
        requesting = MagicMock()

        transfer_ownership(animal, new_owner, set_keeper=True, requesting_profile=requesting)

        animal.allowed_users.add.assert_called_once_with(requesting)


@pytest.mark.unit
class TestAddKeeperService:
    """add_keeper: delegates to M2M.add with the provided keeper id."""

    def test_adds_keeper_by_id(self):
        animal = MagicMock()
        add_keeper(animal, 42)
        animal.allowed_users.add.assert_called_once_with(42)


@pytest.mark.unit
class TestAnimalFieldUpdateServices:
    """set_birthday / set_first_contact: update specific fields and call save."""

    def test_set_birthday_assigns_date_and_saves(self):
        animal = MagicMock()
        bd = date(2020, 6, 15)
        set_birthday(animal, bd)
        assert animal.birthdate == bd
        animal.save.assert_called_once()

    def test_set_first_contact_assigns_both_fields_and_saves(self):
        animal = MagicMock()
        set_first_contact(animal, vet="Dr Smith", place="City Clinic")
        assert animal.first_contact_vet == "Dr Smith"
        assert animal.first_contact_medical_place == "City Clinic"
        animal.save.assert_called_once()
