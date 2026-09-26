from unittest.mock import MagicMock

import pytest

from ahc.apps.veterinary.models import MedicalPlace, Vet
from ahc.apps.veterinary.services import copy_contact_to, create_contact, delete_contact


@pytest.mark.unit
class TestCreateContactService:
    """create_contact: sets owner on the unsaved instance before save(); form input can't override it."""

    def test_assigns_owner_saves_and_returns_record(self):
        owner = MagicMock()
        form = MagicMock()
        record_mock = MagicMock()
        form.save.return_value = record_mock

        result = create_contact(owner, form)

        form.save.assert_called_once_with(commit=False)
        assert record_mock.owner == owner
        record_mock.save.assert_called_once()
        assert result is record_mock

    def test_owner_is_assigned_before_save_is_called(self):
        owner = MagicMock()
        form = MagicMock()
        record_mock = MagicMock()
        form.save.return_value = record_mock
        owner_at_save_time = []
        record_mock.save.side_effect = lambda: owner_at_save_time.append(record_mock.owner)

        create_contact(owner, form)

        assert owner_at_save_time == [owner]


@pytest.mark.unit
class TestDeleteContactService:
    def test_deletes_the_record(self):
        record = MagicMock()

        delete_contact(record)

        record.delete.assert_called_once()


@pytest.mark.integration
@pytest.mark.django_db
class TestCopyContactToService:
    """copy_contact_to: reuse-or-copy identity rule mirroring migration 0009 step 3 (ADR-15 C9)."""

    def test_vet_copy_belongs_to_new_owner_with_identical_fields_and_different_pk(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        original = Vet.objects.create(
            name="Dr Kowalski", phone="111", email="k@example.com", details="Mon-Fri", owner=owner_a
        )

        copy = copy_contact_to(original, owner_b)

        assert copy.owner == owner_b
        assert copy.name == original.name
        assert copy.phone == original.phone
        assert copy.email == original.email
        assert copy.details == original.details
        assert copy.pk != original.pk
        original.refresh_from_db()
        assert original.owner == owner_a

    def test_medical_place_copy_belongs_to_new_owner_with_identical_fields_and_different_pk(
        self, user_profile, second_user_profile
    ):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        original = MedicalPlace.objects.create(
            name="Happy Paws Clinic",
            phone="222",
            email="clinic@example.com",
            details="24/7",
            address="1 Main St",
            website="https://example.com",
            owner=owner_a,
        )

        copy = copy_contact_to(original, owner_b)

        assert copy.owner == owner_b
        assert copy.name == original.name
        assert copy.phone == original.phone
        assert copy.email == original.email
        assert copy.details == original.details
        assert copy.address == original.address
        assert copy.website == original.website
        assert copy.pk != original.pk
        original.refresh_from_db()
        assert original.owner == owner_a

    def test_vet_reuses_an_existing_exact_match_instead_of_creating_a_duplicate(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        original = Vet.objects.create(name="Dr Kowalski", phone="111", owner=owner_a)
        existing = Vet.objects.create(name="Dr Kowalski", phone="111", owner=owner_b)

        result = copy_contact_to(original, owner_b)

        assert result.pk == existing.pk
        assert Vet.objects.filter(owner=owner_b).count() == 1

    def test_medical_place_reuses_an_existing_exact_match_instead_of_creating_a_duplicate(
        self, user_profile, second_user_profile
    ):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        original = MedicalPlace.objects.create(name="Happy Paws Clinic", address="1 Main St", owner=owner_a)
        existing = MedicalPlace.objects.create(name="Happy Paws Clinic", address="1 Main St", owner=owner_b)

        result = copy_contact_to(original, owner_b)

        assert result.pk == existing.pk
        assert MedicalPlace.objects.filter(owner=owner_b).count() == 1

    def test_vet_same_name_but_different_phone_is_not_reused(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        original = Vet.objects.create(name="Dr Kowalski", phone="222", owner=owner_a)
        other = Vet.objects.create(name="Dr Kowalski", phone="111", owner=owner_b)

        result = copy_contact_to(original, owner_b)

        assert result.pk != other.pk
        assert Vet.objects.filter(owner=owner_b).count() == 2

    def test_medical_place_same_name_but_different_address_is_not_reused(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        original = MedicalPlace.objects.create(name="Happy Paws Clinic", address="2 Side St", owner=owner_a)
        other = MedicalPlace.objects.create(name="Happy Paws Clinic", address="1 Main St", owner=owner_b)

        result = copy_contact_to(original, owner_b)

        assert result.pk != other.pk
        assert MedicalPlace.objects.filter(owner=owner_b).count() == 2
