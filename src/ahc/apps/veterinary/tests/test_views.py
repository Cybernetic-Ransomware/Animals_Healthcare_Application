from datetime import date

import pytest
from django.urls import reverse

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.veterinary.models import MedicalPlace, Vet


@pytest.mark.integration
@pytest.mark.django_db
class TestContactBookView:
    def test_owner_sees_their_own_vets_and_medical_places(self, user_profile, logged_in_client):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        client = logged_in_client(user)

        response = client.get(reverse("contact_book"))

        assert response.status_code == 200
        assert vet.name.encode() in response.content
        assert place.name.encode() in response.content

    def test_other_owners_records_are_not_listed(self, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, other_profile = second_user_profile
        Vet.objects.create(name="Dr Nowak", owner=other_profile)
        MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)
        client = logged_in_client(user)

        response = client.get(reverse("contact_book"))

        assert b"Dr Nowak" not in response.content
        assert b"Other Clinic" not in response.content

    def test_anonymous_user_is_redirected_to_login(self, client):
        response = client.get(reverse("contact_book"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_two_vets_with_identical_name_are_both_shown_distinguished_by_phone(self, user_profile, logged_in_client):
        user, profile = user_profile
        Vet.objects.create(name="Dr Kowalski", owner=profile, phone="111111111")
        Vet.objects.create(name="Dr Kowalski", owner=profile, phone="222222222")
        client = logged_in_client(user)

        response = client.get(reverse("contact_book"))

        assert b"111111111" in response.content
        assert b"222222222" in response.content


@pytest.mark.integration
@pytest.mark.django_db
class TestVetCreateView:
    def test_get_requires_login(self, client):
        response = client.get(reverse("vet_create"))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_post_creates_vet_owned_by_the_logged_in_user(self, user_profile, logged_in_client):
        user, profile = user_profile
        client = logged_in_client(user)

        response = client.post(reverse("vet_create"), data={"name": "Dr Kowalski", "phone": "123456789"})

        assert response.status_code == 302
        vet = Vet.objects.get(name="Dr Kowalski")
        assert vet.owner == profile

    def test_second_vet_with_identical_name_can_be_saved(self, user_profile, logged_in_client):
        user, profile = user_profile
        Vet.objects.create(name="Dr Kowalski", owner=profile)
        client = logged_in_client(user)

        response = client.post(reverse("vet_create"), data={"name": "Dr Kowalski"})

        assert response.status_code == 302
        assert Vet.objects.filter(name="Dr Kowalski", owner=profile).count() == 2

    def test_safe_local_next_is_used_after_save(self, user_profile, logged_in_client):
        user, _ = user_profile
        client = logged_in_client(user)

        response = client.post(
            reverse("vet_create") + "?next=/pet/animals/",
            data={"name": "Dr Kowalski", "next": "/pet/animals/"},
        )

        assert response.status_code == 302
        assert response.url == "/pet/animals/"

    def test_external_next_is_ignored(self, user_profile, logged_in_client):
        user, _ = user_profile
        client = logged_in_client(user)

        response = client.post(
            reverse("vet_create"),
            data={"name": "Dr Kowalski", "next": "https://evil.example"},
        )

        assert response.status_code == 302
        assert response.url == reverse("contact_book")


@pytest.mark.integration
@pytest.mark.django_db
class TestMedicalPlaceCreateView:
    def test_post_creates_medical_place_owned_by_the_logged_in_user(self, user_profile, logged_in_client):
        user, profile = user_profile
        client = logged_in_client(user)

        response = client.post(
            reverse("medical_place_create"),
            data={"name": "City Vet Clinic", "address": "Main St 1"},
        )

        assert response.status_code == 302
        place = MedicalPlace.objects.get(name="City Vet Clinic")
        assert place.owner == profile


@pytest.mark.integration
@pytest.mark.django_db
class TestVetUpdateDeleteOwnership:
    def test_owner_can_update_their_own_vet(self, user_profile, logged_in_client):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        client = logged_in_client(user)

        response = client.post(reverse("vet_edit", kwargs={"pk": vet.pk}), data={"name": "Dr Nowak"})

        assert response.status_code == 302
        vet.refresh_from_db()
        assert vet.name == "Dr Nowak"

    def test_owner_can_delete_their_own_vet(self, user_profile, logged_in_client):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        client = logged_in_client(user)

        response = client.post(reverse("vet_delete", kwargs={"pk": vet.pk}))

        assert response.status_code == 302
        assert not Vet.objects.filter(pk=vet.pk).exists()

    def test_get_edit_on_someone_elses_vet_is_404(self, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_vet = Vet.objects.create(name="Dr Nowak", owner=other_profile)
        client = logged_in_client(user)

        response = client.get(reverse("vet_edit", kwargs={"pk": other_vet.pk}))

        assert response.status_code == 404

    def test_post_edit_on_someone_elses_vet_is_404(self, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_vet = Vet.objects.create(name="Dr Nowak", owner=other_profile)
        client = logged_in_client(user)

        response = client.post(reverse("vet_edit", kwargs={"pk": other_vet.pk}), data={"name": "Hijacked"})

        assert response.status_code == 404
        other_vet.refresh_from_db()
        assert other_vet.name == "Dr Nowak"

    def test_get_delete_on_someone_elses_vet_is_404(self, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_vet = Vet.objects.create(name="Dr Nowak", owner=other_profile)
        client = logged_in_client(user)

        response = client.get(reverse("vet_delete", kwargs={"pk": other_vet.pk}))

        assert response.status_code == 404

    def test_post_delete_on_someone_elses_vet_is_404(self, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_vet = Vet.objects.create(name="Dr Nowak", owner=other_profile)
        client = logged_in_client(user)

        response = client.post(reverse("vet_delete", kwargs={"pk": other_vet.pk}))

        assert response.status_code == 404
        assert Vet.objects.filter(pk=other_vet.pk).exists()

    def test_carer_with_vet_contact_access_cannot_reach_owners_vet_record(
        self, user_profile, second_user_profile, logged_in_client
    ):
        """A carer sees first-contact data through the animal, but never the owner's contact book."""
        carer_user, carer_profile = second_user_profile
        _, owner_profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=owner_profile)
        animal = Animal.objects.create(full_name="Whiskers", owner=owner_profile, first_contact_vet=vet)
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_vet_contact=True)
        client = logged_in_client(carer_user)

        response = client.get(reverse("vet_edit", kwargs={"pk": vet.pk}))

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestMedicalPlaceUpdateDeleteOwnership:
    def test_owner_can_update_their_own_medical_place(self, user_profile, logged_in_client):
        user, profile = user_profile
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        client = logged_in_client(user)

        response = client.post(reverse("medical_place_edit", kwargs={"pk": place.pk}), data={"name": "New Name"})

        assert response.status_code == 302
        place.refresh_from_db()
        assert place.name == "New Name"

    def test_get_edit_on_someone_elses_medical_place_is_404(self, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_place = MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)
        client = logged_in_client(user)

        response = client.get(reverse("medical_place_edit", kwargs={"pk": other_place.pk}))

        assert response.status_code == 404

    def test_post_delete_on_someone_elses_medical_place_is_404(self, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_place = MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)
        client = logged_in_client(user)

        response = client.post(reverse("medical_place_delete", kwargs={"pk": other_place.pk}))

        assert response.status_code == 404
        assert MedicalPlace.objects.filter(pk=other_place.pk).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestContactDeleteConfirmation:
    def test_shows_living_and_archived_animals_referencing_the_vet(self, user_profile, logged_in_client):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        living = Animal.objects.create(full_name="Whiskers", owner=profile, first_contact_vet=vet)
        archived = Animal.objects.create(
            full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15), first_contact_vet=vet
        )
        client = logged_in_client(user)

        response = client.get(reverse("vet_delete", kwargs={"pk": vet.pk}))

        assert living.full_name.encode() in response.content
        assert archived.full_name.encode() in response.content

    def test_deleting_a_used_vet_clears_the_animals_foreign_key_without_deleting_the_animal(
        self, user_profile, logged_in_client
    ):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        animal = Animal.objects.create(full_name="Whiskers", owner=profile, first_contact_vet=vet)
        client = logged_in_client(user)

        response = client.post(reverse("vet_delete", kwargs={"pk": vet.pk}))

        assert response.status_code == 302
        assert not Vet.objects.filter(pk=vet.pk).exists()
        animal.refresh_from_db()
        assert animal.first_contact_vet is None
