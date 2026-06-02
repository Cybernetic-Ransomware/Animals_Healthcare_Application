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
    remove_keeper,
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
        with patch("ahc.apps.animals.selectors.active_share_for", return_value=MagicMock()):
            assert user_can_access_animal(profile, animal) is True

    def test_stranger_cannot_access(self):
        profile = MagicMock()
        animal = MagicMock()
        animal.owner = MagicMock()
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
class TestOtherRecordsForSelector:
    """other_records_for: excludes medical_visit and diet_note types."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Buddy", owner=profile)

    def test_excludes_medical_visit_and_diet_note(self, animal, user_profile):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.selectors import other_records_for

        _, profile = user_profile
        MedicalRecord.objects.create(
            animal=animal, author=profile, short_description="Visit", type_of_event="medical_visit"
        )
        MedicalRecord.objects.create(animal=animal, author=profile, short_description="Diet", type_of_event="diet_note")
        note = MedicalRecord.objects.create(
            animal=animal, author=profile, short_description="Other", type_of_event="fast_note"
        )

        results = list(other_records_for(animal))
        ids = [r.id for r in results]
        assert note.id in ids
        assert len(results) == 1

    def test_returns_empty_when_only_special_types(self, animal, user_profile):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.selectors import other_records_for

        _, profile = user_profile
        MedicalRecord.objects.create(animal=animal, author=profile, short_description="V", type_of_event="medical_visit")
        assert list(other_records_for(animal)) == []


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalTabView:
    """AnimalTabView: htmx vs full-page response, access control."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Luna", owner=profile)

    def _client_for(self, user):
        from django.test import Client

        c = Client()
        c.force_login(user)
        return c

    def test_htmx_request_returns_fragment_without_base_title(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        url = f"/pet/{animal.id}/tab/mainpage/"
        response = c.get(url, HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<title>" not in content

    def test_non_htmx_request_returns_full_page_with_base_title(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        url = f"/pet/{animal.id}/tab/mainpage/"
        response = c.get(url)
        assert response.status_code == 200
        assert "<title>" in response.content.decode()

    def test_all_public_slugs_return_200_for_owner(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        for slug in ("mainpage", "vet", "diet", "notes", "ownership", "settings"):
            url = f"/pet/{animal.id}/tab/{slug}/"
            response = c.get(url, HTTP_HX_REQUEST="true")
            assert response.status_code == 200, f"Expected 200 for slug={slug!r}, got {response.status_code}"

    def test_owner_only_tabs_return_403_for_keeper(self, animal, second_user_profile):
        other_user, other_profile = second_user_profile
        animal.allowed_users.add(other_profile)
        c = self._client_for(other_user)
        for slug in ("ownership", "settings"):
            url = f"/pet/{animal.id}/tab/{slug}/"
            response = c.get(url, HTTP_HX_REQUEST="true")
            assert response.status_code == 403, f"Expected 403 for keeper on slug={slug!r}, got {response.status_code}"

    def test_non_accessible_user_gets_403(self, animal, second_user_profile):
        other_user, _ = second_user_profile
        c = self._client_for(other_user)
        url = f"/pet/{animal.id}/tab/mainpage/"
        response = c.get(url)
        assert response.status_code == 403

    def test_unknown_slug_returns_404(self, animal, user_profile):
        user, _ = user_profile
        c = self._client_for(user)
        url = f"/pet/{animal.id}/tab/nonexistent/"
        response = c.get(url)
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestRemoveKeeperView:
    """RemoveKeeperView: owner POST removes keeper; non-owner gets 403."""

    @pytest.fixture
    def animal_with_keeper(self, db, user_profile, second_user_profile):
        _, owner_profile = user_profile
        _, keeper_profile = second_user_profile
        a = Animal.objects.create(full_name="Rex", owner=owner_profile)
        a.allowed_users.add(keeper_profile)
        return a

    def test_owner_post_removes_keeper_and_redirects(self, animal_with_keeper, user_profile, second_user_profile):
        from django.test import Client

        owner_user, _ = user_profile
        _, keeper_profile = second_user_profile
        c = Client()
        c.force_login(owner_user)
        url = f"/pet/{animal_with_keeper.id}/keepers/{keeper_profile.pk}/remove/"
        response = c.post(url)
        assert response.status_code == 302
        animal_with_keeper.refresh_from_db()
        assert not animal_with_keeper.allowed_users.filter(pk=keeper_profile.pk).exists()

    def test_non_owner_post_returns_403(self, animal_with_keeper, second_user_profile):
        from django.test import Client

        keeper_user, _ = second_user_profile
        c = Client()
        c.force_login(keeper_user)
        _, keeper_profile = second_user_profile
        url = f"/pet/{animal_with_keeper.id}/keepers/{keeper_profile.pk}/remove/"
        response = c.post(url)
        assert response.status_code == 403
