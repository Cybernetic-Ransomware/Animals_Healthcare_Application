import pytest
from django.urls import reverse

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.veterinary.models import MedicalPlace, Vet


@pytest.mark.integration
@pytest.mark.django_db
class TestVetTabAccess:
    """Vet-tab visibility after the veterinary contact refactor (structured Vet/MedicalPlace records)."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        vet = Vet.objects.create(name="Dr Smith", owner=profile, phone="123-456-789")
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        return Animal.objects.create(
            full_name="Luna",
            owner=profile,
            first_contact_vet=vet,
            first_contact_medical_place=place,
            legacy_first_contact_vet="LEGACY TEXT SENTINEL VET",
            legacy_first_contact_medical_place="LEGACY TEXT SENTINEL PLACE",
        )

    def test_owner_sees_contact_section_and_edit_link(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        c = logged_in_client(user)
        response = c.get(f"/pet/{animal.id}/tab/vet/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Veterinary contact" in content
        assert reverse("animal_first_contact", kwargs={"pk": animal.id}) in content
        assert "LEGACY TEXT SENTINEL" not in content

    def test_keeper_with_allow_vet_contact_sees_structured_contact_but_not_edit_link(
        self, animal, second_user_profile, logged_in_client
    ):
        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_vet_contact=True)
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/tab/vet/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Veterinary contact" in content
        assert "Dr Smith" in content
        assert "123-456-789" in content
        assert "City Vet Clinic" in content
        assert "LEGACY TEXT SENTINEL" not in content
        assert reverse("animal_first_contact", kwargs={"pk": animal.id}) not in content
        assert reverse("contact_book") not in content

    def test_keeper_with_only_allow_history_does_not_see_contact_but_sees_timeline(
        self, animal, second_user_profile, logged_in_client
    ):
        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_vet_contact=False, allow_history=True)
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/tab/vet/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Veterinary contact" not in content
        assert "Dr Smith" not in content
        assert "City Vet Clinic" not in content
        assert "Medical visit timeline" in content

    def test_keeper_without_vet_contact_and_without_history_gets_403(self, animal, second_user_profile, logged_in_client):
        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_vet_contact=False, allow_history=False)
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/tab/vet/", HTTP_HX_REQUEST="true")
        assert response.status_code == 403

    def test_keeper_with_vet_contact_gets_403_on_change_first_contact_view(
        self, animal, second_user_profile, logged_in_client
    ):
        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_vet_contact=True)
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/cnt/")
        assert response.status_code == 403
