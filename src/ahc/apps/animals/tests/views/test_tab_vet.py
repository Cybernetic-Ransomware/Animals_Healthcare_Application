import pytest
from django.urls import reverse

from ahc.apps.animals.models import Animal, AnimalShare


@pytest.mark.integration
@pytest.mark.django_db
class TestVetTabAccess:
    """Characterizes pre-refactor vet-tab visibility before plan C1 (doc/plans/vet_medical_place_profiles.md)."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(
            full_name="Luna",
            owner=profile,
            first_contact_vet="Dr. Smith, tel. 123-456-789",
            first_contact_medical_place="City Vet Clinic",
        )

    def test_owner_sees_contact_section_and_edit_link(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        c = logged_in_client(user)
        response = c.get(f"/pet/{animal.id}/tab/vet/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Veterinary contact" in content
        assert reverse("animal_first_contact", kwargs={"pk": animal.id}) in content

    def test_keeper_with_allow_vet_contact_sees_text_but_not_edit_link(self, animal, second_user_profile, logged_in_client):
        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_vet_contact=True)
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/tab/vet/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Veterinary contact" in content
        assert "Dr. Smith, tel. 123-456-789" in content
        assert reverse("animal_first_contact", kwargs={"pk": animal.id}) not in content

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
