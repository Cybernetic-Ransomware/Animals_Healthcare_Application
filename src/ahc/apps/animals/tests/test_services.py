from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from ahc.apps.animals.selectors import (
    animals_visible_to,
)
from ahc.apps.animals.services import (
    add_keeper,
    create_animal,
    pin_animal,
    process_profile_image,
    remove_keeper,
    set_birthday,
    set_deceased,
    set_first_contact,
    set_memorial_note,
    transfer_ownership,
    unpin_animal,
    unset_deceased,
)


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

        with patch("ahc.apps.animals.services.create_share") as mock_create_share:
            transfer_ownership(animal, new_owner, set_keeper=True, requesting_profile=requesting)
            mock_create_share.assert_called_once_with(animal, requesting.pk, scope=None, valid_until=None)


@pytest.mark.unit
class TestAddKeeperService:
    """add_keeper: delegates to create_share with the provided keeper id and default scope."""

    def test_adds_keeper_by_id(self):
        animal = MagicMock()
        with patch("ahc.apps.animals.services.create_share") as mock_create_share:
            add_keeper(animal, 42)
            mock_create_share.assert_called_once_with(animal, 42, scope=None, valid_until=None)


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


@pytest.mark.unit
class TestNewAnimalServices:
    """remove_keeper / set_next_visit / set_dietary_restrictions: unit coverage."""

    def test_remove_keeper_delegates_to_animalshare(self):
        animal = MagicMock()
        with patch("ahc.apps.animals.services.AnimalShare") as mock_model:
            remove_keeper(animal, 99)
            mock_model.objects.filter.assert_called_once_with(animal=animal, carer_id=99)
            mock_model.objects.filter.return_value.delete.assert_called_once()

    def test_set_next_visit_assigns_date_and_saves(self):
        from datetime import date as date_type

        from ahc.apps.animals.services import set_next_visit

        animal = MagicMock()
        d = date_type(2026, 9, 1)
        set_next_visit(animal, d)
        assert animal.next_visit_date == d
        animal.save.assert_called_once()

    def test_set_dietary_restrictions_assigns_text_and_saves(self):
        from ahc.apps.animals.services import set_dietary_restrictions

        animal = MagicMock()
        set_dietary_restrictions(animal, "No grapes, no onions")
        assert animal.dietary_restrictions == "No grapes, no onions"
        animal.save.assert_called_once()

    def test_remove_keeper_does_not_affect_owner(self):
        """Removing a keeper must not touch the owner field."""
        animal = MagicMock()
        original_owner = MagicMock()
        animal.owner = original_owner
        with patch("ahc.apps.animals.services.AnimalShare"):
            remove_keeper(animal, 42)
        assert animal.owner is original_owner


@pytest.mark.integration
@pytest.mark.django_db
class TestDeceasedServices:
    """set_deceased / set_memorial_note / unset_deceased services."""

    def test_set_deceased_records_date_and_note(self, animal):
        set_deceased(animal, date_of_death=date(2024, 5, 1), memorial_note="Rest in peace")
        animal.refresh_from_db()
        assert animal.date_of_death == date(2024, 5, 1)
        assert animal.memorial_note == "Rest in peace"
        assert animal.is_deceased is True

    def test_set_deceased_does_not_delete_shares(self, animal, second_user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        share = AnimalShare.objects.create(animal=animal, carer=carer_profile)
        set_deceased(animal, date_of_death=date(2024, 5, 1), memorial_note=None)
        assert AnimalShare.objects.filter(pk=share.pk).exists()

    def test_unset_deceased_clears_date_and_restores_visibility(self, animal, user_profile, second_user_profile):
        from ahc.apps.animals.models import AnimalShare

        _, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile)
        set_deceased(animal, date_of_death=date(2024, 5, 1), memorial_note="Farewell")
        assert animal not in animals_visible_to(carer_profile)

        unset_deceased(animal)
        animal.refresh_from_db()
        assert animal.date_of_death is None
        assert animal.memorial_note == "Farewell"  # preserved after un-archive
        assert animal in animals_visible_to(carer_profile)

    def test_set_memorial_note_updates_note_only(self, animal):
        set_deceased(animal, date_of_death=date(2024, 5, 1), memorial_note="Original")
        set_memorial_note(animal, memorial_note="Updated")
        animal.refresh_from_db()
        assert animal.memorial_note == "Updated"
        assert animal.date_of_death == date(2024, 5, 1)
