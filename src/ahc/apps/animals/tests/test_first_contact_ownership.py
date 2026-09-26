"""Invariant I2: first-contact Vet/MedicalPlace must belong to animal.owner (service and view boundaries)."""

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.animals.services import set_first_contact
from ahc.apps.veterinary.models import MedicalPlace, Vet


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
