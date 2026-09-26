from datetime import date

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.veterinary.models import MedicalPlace, Vet


@pytest.mark.integration
@pytest.mark.django_db
class TestFirstContactForeignKeys:
    """Deleting a contact record must SET_NULL on Animal, never cascade-delete the animal."""

    def test_deleting_vet_nulls_first_contact_vet_and_keeps_animal(self, animal, user_profile):
        _, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        animal.first_contact_vet = vet
        animal.save()

        vet.delete()
        animal.refresh_from_db()

        assert animal.first_contact_vet is None
        assert Animal.objects.filter(pk=animal.pk).exists()

    def test_deleting_medical_place_nulls_first_contact_medical_place_and_keeps_animal(self, animal, user_profile):
        _, profile = user_profile
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        animal.first_contact_medical_place = place
        animal.save()

        place.delete()
        animal.refresh_from_db()

        assert animal.first_contact_medical_place is None
        assert Animal.objects.filter(pk=animal.pk).exists()


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


@pytest.mark.unit
class TestIsDeceasedProperty:
    """Animal.is_deceased: reflects date_of_death presence."""

    def test_false_when_no_date_of_death(self):
        animal = Animal(full_name="Live")
        assert animal.is_deceased is False

    def test_true_when_date_of_death_set(self):
        animal = Animal(full_name="Gone", date_of_death=date(2024, 1, 1))
        assert animal.is_deceased is True
