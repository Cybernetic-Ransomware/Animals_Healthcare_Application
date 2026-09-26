"""Invariant I2: first-contact Vet/MedicalPlace must belong to animal.owner (service and view boundaries)."""

from unittest.mock import patch

import pytest

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.animals.services import set_first_contact, transfer_ownership
from ahc.apps.veterinary.models import MedicalPlace, Vet
from ahc.apps.veterinary.services import copy_contact_to as real_copy_contact_to


@pytest.mark.integration
@pytest.mark.django_db
class TestFirstContactOwnershipInvariant:
    def test_service_rejects_a_vet_owned_by_a_different_profile(self, user_profile, second_user_profile):
        _, owner_profile = user_profile
        _, other_profile = second_user_profile
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_profile)
        foreign_vet = Vet.objects.create(name="Dr Nowak", owner=other_profile)

        with pytest.raises(ValueError):
            set_first_contact(animal, vet=foreign_vet, place=None)

        animal.refresh_from_db()
        assert animal.first_contact_vet is None

    def test_service_rejects_a_medical_place_owned_by_a_different_profile(self, user_profile, second_user_profile):
        _, owner_profile = user_profile
        _, other_profile = second_user_profile
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_profile)
        foreign_place = MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)

        with pytest.raises(ValueError):
            set_first_contact(animal, vet=None, place=foreign_place)

        animal.refresh_from_db()
        assert animal.first_contact_medical_place is None

    def test_view_boundary_rejects_a_foreign_vet_uuid_submitted_by_hand(
        self, user_profile, second_user_profile, logged_in_client
    ):
        user, owner_profile = user_profile
        _, other_profile = second_user_profile
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_profile)
        foreign_vet = Vet.objects.create(name="Dr Nowak", owner=other_profile)

        response = logged_in_client(user).post(f"/pet/{animal.id}/cnt/", {"first_contact_vet": foreign_vet.pk})

        assert response.status_code == 200
        animal.refresh_from_db()
        assert animal.first_contact_vet is None

    def test_view_boundary_rejects_a_foreign_medical_place_uuid_submitted_by_hand(
        self, user_profile, second_user_profile, logged_in_client
    ):
        user, owner_profile = user_profile
        _, other_profile = second_user_profile
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_profile)
        foreign_place = MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)

        response = logged_in_client(user).post(f"/pet/{animal.id}/cnt/", {"first_contact_medical_place": foreign_place.pk})

        assert response.status_code == 200
        animal.refresh_from_db()
        assert animal.first_contact_medical_place is None


@pytest.mark.integration
@pytest.mark.django_db
class TestTransferOwnershipCopiesFirstContact:
    """I2 after transfer_ownership: first-contact FKs are re-pointed to new_owner's book (ADR-15 C9)."""

    def test_transfer_copies_vet_and_medical_place_and_preserves_their_fields(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        vet = Vet.objects.create(name="Dr Kowalski", phone="111", email="k@example.com", details="Mon-Fri", owner=owner_a)
        place = MedicalPlace.objects.create(
            name="Happy Paws Clinic", address="1 Main St", website="https://example.com", owner=owner_a
        )
        animal = Animal.objects.create(
            full_name="Whiskers", owner=owner_a, first_contact_vet=vet, first_contact_medical_place=place
        )

        transfer_ownership(animal, owner_b, set_keeper=False, requesting_profile=owner_a)

        animal.refresh_from_db()
        assert animal.owner == owner_b
        assert animal.first_contact_vet.owner == owner_b
        assert animal.first_contact_vet.name == "Dr Kowalski"
        assert animal.first_contact_vet.phone == "111"
        assert animal.first_contact_vet.email == "k@example.com"
        assert animal.first_contact_vet.details == "Mon-Fri"
        assert animal.first_contact_medical_place.owner == owner_b
        assert animal.first_contact_medical_place.name == "Happy Paws Clinic"
        assert animal.first_contact_medical_place.address == "1 Main St"
        assert animal.first_contact_medical_place.website == "https://example.com"

    def test_original_records_remain_owned_by_the_previous_owner(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=owner_a)
        place = MedicalPlace.objects.create(name="Happy Paws Clinic", owner=owner_a)
        animal = Animal.objects.create(
            full_name="Whiskers", owner=owner_a, first_contact_vet=vet, first_contact_medical_place=place
        )

        transfer_ownership(animal, owner_b, set_keeper=False, requesting_profile=owner_a)

        vet.refresh_from_db()
        place.refresh_from_db()
        assert vet.owner == owner_a
        assert place.owner == owner_a

    def test_two_animals_sharing_a_vet_both_reuse_the_same_copy_after_transfer(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        vet = Vet.objects.create(name="Dr Kowalski", phone="111", owner=owner_a)
        animal_1 = Animal.objects.create(full_name="Whiskers", owner=owner_a, first_contact_vet=vet)
        animal_2 = Animal.objects.create(full_name="Rex", owner=owner_a, first_contact_vet=vet)

        transfer_ownership(animal_1, owner_b, set_keeper=False, requesting_profile=owner_a)
        transfer_ownership(animal_2, owner_b, set_keeper=False, requesting_profile=owner_a)

        animal_1.refresh_from_db()
        animal_2.refresh_from_db()
        assert animal_1.first_contact_vet == animal_2.first_contact_vet
        assert Vet.objects.filter(owner=owner_b, name="Dr Kowalski", phone="111").count() == 1

    def test_transfer_reuses_an_existing_exact_match_owned_by_the_new_owner(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        vet = Vet.objects.create(name="Dr Kowalski", phone="111", owner=owner_a)
        existing = Vet.objects.create(name="Dr Kowalski", phone="111", owner=owner_b)
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_a, first_contact_vet=vet)

        transfer_ownership(animal, owner_b, set_keeper=False, requesting_profile=owner_a)

        animal.refresh_from_db()
        assert animal.first_contact_vet == existing
        assert Vet.objects.filter(owner=owner_b).count() == 1

    def test_transfer_creates_a_separate_copy_when_the_new_owner_has_the_same_name_but_different_data(
        self, user_profile, second_user_profile
    ):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        vet = Vet.objects.create(name="Dr Kowalski", phone="222", owner=owner_a)
        unrelated = Vet.objects.create(name="Dr Kowalski", phone="111", owner=owner_b)
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_a, first_contact_vet=vet)

        transfer_ownership(animal, owner_b, set_keeper=False, requesting_profile=owner_a)

        animal.refresh_from_db()
        assert animal.first_contact_vet != unrelated
        assert animal.first_contact_vet.phone == "222"
        assert Vet.objects.filter(owner=owner_b).count() == 2

    def test_transfer_with_no_first_contact_only_changes_the_owner(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_a)

        transfer_ownership(animal, owner_b, set_keeper=False, requesting_profile=owner_a)

        animal.refresh_from_db()
        assert animal.owner == owner_b
        assert animal.first_contact_vet is None
        assert animal.first_contact_medical_place is None


@pytest.mark.integration
@pytest.mark.django_db
class TestTransferOwnershipAndOldContactDeletion:
    """I5: deleting the previous owner's original contact must not clear a transferred animal's first contact."""

    def test_deleting_the_original_vet_does_not_clear_the_transferred_animals_first_contact(
        self, user_profile, second_user_profile
    ):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        original_vet = Vet.objects.create(name="Dr Kowalski", owner=owner_a)
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_a, first_contact_vet=original_vet)

        transfer_ownership(animal, owner_b, set_keeper=False, requesting_profile=owner_a)
        animal.refresh_from_db()
        copied_vet = animal.first_contact_vet
        assert copied_vet.pk != original_vet.pk

        original_vet.delete()

        assert Animal.objects.filter(pk=animal.pk).exists()
        animal.refresh_from_db()
        assert animal.first_contact_vet == copied_vet


@pytest.mark.integration
@pytest.mark.django_db
class TestTransferOwnershipSetKeeper:
    def test_set_keeper_still_creates_a_share_alongside_the_contact_copy(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=owner_a)
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_a, first_contact_vet=vet)

        transfer_ownership(animal, owner_b, set_keeper=True, requesting_profile=owner_a)

        animal.refresh_from_db()
        assert animal.owner == owner_b
        assert animal.first_contact_vet.owner == owner_b
        assert AnimalShare.objects.filter(animal=animal, carer=owner_a).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestTransferOwnershipAtomicity:
    """transfer_ownership runs the owner change and both contact copies in one transaction.atomic block."""

    def test_a_failure_copying_the_second_contact_rolls_back_the_whole_transfer(self, user_profile, second_user_profile):
        _, owner_a = user_profile
        _, owner_b = second_user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=owner_a)
        place = MedicalPlace.objects.create(name="Happy Paws Clinic", owner=owner_a)
        animal = Animal.objects.create(
            full_name="Whiskers", owner=owner_a, first_contact_vet=vet, first_contact_medical_place=place
        )

        def fake_copy_contact_to(record, new_owner):
            if record.pk == place.pk:
                raise RuntimeError("boom")
            return real_copy_contact_to(record, new_owner)

        with (
            patch("ahc.apps.animals.services.copy_contact_to", side_effect=fake_copy_contact_to),
            pytest.raises(RuntimeError),
        ):
            transfer_ownership(animal, owner_b, set_keeper=False, requesting_profile=owner_a)

        animal.refresh_from_db()
        assert animal.owner == owner_a
        assert animal.first_contact_vet == vet
        assert animal.first_contact_medical_place == place
        assert not Vet.objects.filter(owner=owner_b).exists()
