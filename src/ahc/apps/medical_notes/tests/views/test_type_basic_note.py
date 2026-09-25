import pytest
from django.urls import reverse

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord


@pytest.mark.integration
@pytest.mark.django_db
class TestCreateNoteFormViewBiometricGate:
    """CreateNoteFormView: biometric shell-note gate — carers need allow_biometrics; other types unaffected."""

    @pytest.fixture
    def animal_with_share(self, db, user_profile, second_user_profile):
        _, owner_profile = user_profile
        _, carer_profile = second_user_profile
        animal = Animal.objects.create(full_name="GatedAnimal", owner=owner_profile)
        share = AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=False, allow_basic=True)
        return animal, share, carer_profile

    def test_carer_without_biometrics_gets_403_on_biometric_type(self, client, second_user_profile, animal_with_share):
        carer_user, _ = second_user_profile
        animal, _, _ = animal_with_share
        client.force_login(carer_user)

        response = client.get(f"/note/{animal.id}/create/?type_of_event=biometric_record")
        assert response.status_code == 403

    def test_carer_with_biometrics_can_create_shell_note(self, client, second_user_profile, animal_with_share):
        carer_user, _ = second_user_profile
        animal, share, _ = animal_with_share
        share.allow_biometrics = True
        share.save()
        client.force_login(carer_user)

        response = client.get(f"/note/{animal.id}/create/?type_of_event=biometric_record")
        assert response.status_code == 200

    def test_carer_without_biometrics_can_create_other_note_types(self, client, second_user_profile, animal_with_share):
        """allow_biometrics gate must not affect non-biometric note types."""
        carer_user, _ = second_user_profile
        animal, _, _ = animal_with_share
        client.force_login(carer_user)

        response = client.get(f"/note/{animal.id}/create/?type_of_event=fast_note")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestRelatedAnimalsLabels:
    """Regression for D-02: animal choice widgets must show full_name, not the model repr."""

    @pytest.fixture
    def two_owned_animals_for_notes(self, db, user_profile):
        _, profile = user_profile
        primary = Animal.objects.create(full_name="Maru", owner=profile)
        other = Animal.objects.create(full_name="Chilli", owner=profile)
        return primary, other, profile

    def test_create_note_form_shows_animal_full_name(self, client, user_profile, two_owned_animals_for_notes):
        user, _ = user_profile
        primary, other, _ = two_owned_animals_for_notes
        client.force_login(user)

        response = client.get(f"/note/{primary.id}/create/", HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert other.full_name.encode() in response.content
        assert b"Animal object" not in response.content

    def test_edit_related_animals_shows_animal_full_name(self, client, user_profile, two_owned_animals_for_notes):
        user, profile = user_profile
        primary, other, _ = two_owned_animals_for_notes
        note = MedicalRecord.objects.create(
            animal=primary, author=profile, type_of_event="fast_note", short_description="x"
        )
        client.force_login(user)

        response = client.get(reverse("note_animals_edit", kwargs={"pk": note.id}))

        assert response.status_code == 200
        assert primary.full_name.encode() in response.content
        assert other.full_name.encode() in response.content
        assert b"Animal object" not in response.content


@pytest.mark.integration
@pytest.mark.django_db
class TestCreateNoteFormViewLegend:
    """Regression for F-01: the modal fieldset legend must not repeat the dialog title."""

    @pytest.fixture
    def owned_animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Maru", owner=profile)

    @pytest.mark.parametrize(
        "type_of_event",
        ["", "medical_visit", "diet_note", "medicament_note", "fast_note"],
    )
    def test_legend_is_generic_section_label(self, client, user_profile, owned_animal, type_of_event):
        user, _ = user_profile
        client.force_login(user)

        url = f"/note/{owned_animal.id}/create/"
        if type_of_event:
            url += f"?type_of_event={type_of_event}"
        response = client.get(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert response.context["legend"] == "Note details"
