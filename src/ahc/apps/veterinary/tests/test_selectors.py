from datetime import date

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.veterinary.models import MedicalPlace, Vet
from ahc.apps.veterinary.selectors import animals_referencing, medical_places_for, vets_for


@pytest.mark.integration
@pytest.mark.django_db
class TestVetsFor:
    def test_returns_only_the_owners_vets(self, user_profile, second_user_profile):
        _, profile = user_profile
        _, other_profile = second_user_profile
        own_vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        Vet.objects.create(name="Dr Nowak", owner=other_profile)

        assert list(vets_for(profile)) == [own_vet]

    def test_two_vets_with_identical_name_for_one_owner_both_come_back(self, user_profile):
        _, profile = user_profile
        first = Vet.objects.create(name="Dr Kowalski", owner=profile)
        second = Vet.objects.create(name="Dr Kowalski", owner=profile)

        assert set(vets_for(profile)) == {first, second}


@pytest.mark.integration
@pytest.mark.django_db
class TestMedicalPlacesFor:
    def test_returns_only_the_owners_medical_places(self, user_profile, second_user_profile):
        _, profile = user_profile
        _, other_profile = second_user_profile
        own_place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)

        assert list(medical_places_for(profile)) == [own_place]

    def test_two_places_with_identical_name_for_one_owner_both_come_back(self, user_profile):
        _, profile = user_profile
        first = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        second = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)

        assert set(medical_places_for(profile)) == {first, second}


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalsReferencing:
    def test_returns_living_and_archived_animals(self, user_profile):
        _, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        living = Animal.objects.create(full_name="Whiskers", owner=profile, first_contact_vet=vet)
        archived = Animal.objects.create(
            full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15), first_contact_vet=vet
        )

        assert set(animals_referencing(vet)) == {living, archived}

    def test_medical_place_reference_also_included(self, user_profile):
        _, profile = user_profile
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        animal = Animal.objects.create(full_name="Whiskers", owner=profile, first_contact_medical_place=place)

        assert set(animals_referencing(place)) == {animal}
