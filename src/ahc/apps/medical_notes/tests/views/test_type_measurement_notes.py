from decimal import Decimal

import pytest
from django.urls import reverse

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_measurement_notes import (
    BiometricHeightRecords,
    BiometricRecord,
    BiometricWeightRecords,
)


@pytest.fixture
def two_owned_animals(db, user_profile):
    """Two animals owned by user_profile for view tests."""
    _, profile = user_profile
    a1 = Animal.objects.create(full_name="Dog", owner=profile)
    a2 = Animal.objects.create(full_name="Cat", owner=profile)
    return (a1, a2), profile


@pytest.mark.integration
@pytest.mark.django_db
class TestBiometricBatchCreateView:
    """BiometricBatchCreateView: GET renders formset rows, POST creates pairs, stranger blocked."""

    def test_get_renders_one_row_per_animal(self, client, user_profile, two_owned_animals):
        user, _ = user_profile
        client.force_login(user)
        response = client.get(reverse("biometric_batch"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "Dog" in content
        assert "Cat" in content

    def test_post_creates_pairs_for_checked_rows_only(self, client, user_profile, two_owned_animals):
        user, _ = user_profile
        (a1, a2), _ = two_owned_animals
        client.force_login(user)

        data = {
            "record_type": "weight",
            "unit": "kg",
            "custom_name": "",
            "custom_unit": "",
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-include": "on",
            "form-0-animal_id": str(a1.id),
            "form-0-value": "12.5",
            "form-1-include": "",
            "form-1-animal_id": str(a2.id),
            "form-1-value": "",
        }
        response = client.post(reverse("biometric_batch"), data)

        assert response.status_code == 302
        assert MedicalRecord.objects.filter(type_of_event="biometric_record").count() == 1
        assert BiometricRecord.objects.filter(animal=a1).count() == 1
        assert BiometricRecord.objects.filter(animal=a2).count() == 0

    def test_post_ignores_animal_outside_allowed_set(self, client, user_profile, second_user_profile, two_owned_animals):
        """A row carrying a stranger's animal_id must produce no records."""
        user, _ = user_profile
        _, other_profile = second_user_profile

        stranger_animal = Animal.objects.create(full_name="Stranger", owner=other_profile)
        client.force_login(user)

        data = {
            "record_type": "weight",
            "unit": "kg",
            "custom_name": "",
            "custom_unit": "",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-include": "on",
            "form-0-animal_id": str(stranger_animal.id),
            "form-0-value": "5.0",
        }
        response = client.post(reverse("biometric_batch"), data)

        assert response.status_code == 302
        assert BiometricRecord.objects.count() == 0

    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get(reverse("biometric_batch"))
        assert response.status_code == 302
        assert "/login" in response["Location"]


@pytest.mark.integration
@pytest.mark.django_db
class TestBiometricBatchCarerPermissions:
    """BiometricBatchCreateView: carer without allow_biometrics is blocked end-to-end."""

    @pytest.fixture
    def shared_animal_no_biometrics(self, db, user_profile, second_user_profile):
        _, owner_profile = user_profile
        _, carer_profile = second_user_profile
        animal = Animal.objects.create(full_name="SharedPet", owner=owner_profile)
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=False)
        return animal, carer_profile

    def test_carer_without_biometrics_gets_no_rows(self, client, second_user_profile, shared_animal_no_biometrics):
        """GET must not offer the animal when carer lacks allow_biometrics."""
        carer_user, _ = second_user_profile
        animal, _ = shared_animal_no_biometrics
        client.force_login(carer_user)
        response = client.get(reverse("biometric_batch"))

        assert response.status_code == 200
        offered_ids = {str(a.id) for _, a in response.context["rows"]}
        assert str(animal.id) not in offered_ids

    def test_carer_without_biometrics_post_creates_no_records(
        self, client, second_user_profile, shared_animal_no_biometrics
    ):
        """POST with a no-biometrics animal_id must produce zero records."""
        carer_user, _ = second_user_profile
        animal, _ = shared_animal_no_biometrics
        client.force_login(carer_user)

        data = {
            "record_type": "weight",
            "unit": "kg",
            "custom_name": "",
            "custom_unit": "",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-include": "on",
            "form-0-animal_id": str(animal.id),
            "form-0-value": "5.0",
        }
        response = client.post(reverse("biometric_batch"), data)

        assert response.status_code == 302
        assert BiometricRecord.objects.count() == 0


@pytest.mark.integration
@pytest.mark.django_db
class TestBiometricRecordCreateViewPermissions:
    """BiometricRecordCreateView: allow_biometrics flag enforced at mixin level."""

    @pytest.fixture
    def animal_and_shell_note(self, db, user_profile):
        _, owner_profile = user_profile
        animal = Animal.objects.create(full_name="BioAnimal", owner=owner_profile)
        shell = MedicalRecord.objects.create(
            animal=animal, author=owner_profile, short_description="shell", type_of_event="biometric_record"
        )
        return animal, shell

    def test_carer_without_biometrics_gets_403(self, client, second_user_profile, user_profile, animal_and_shell_note):
        carer_user, carer_profile = second_user_profile
        animal, shell = animal_and_shell_note
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=False)
        client.force_login(carer_user)

        response = client.get(f"/note/{animal.id}/{shell.id}/medical_create/")
        assert response.status_code == 403

    def test_owner_can_access(self, client, user_profile, animal_and_shell_note):
        owner_user, _ = user_profile
        animal, shell = animal_and_shell_note
        client.force_login(owner_user)

        response = client.get(f"/note/{animal.id}/{shell.id}/medical_create/")
        assert response.status_code == 200

    def test_carer_with_biometrics_can_access(self, client, second_user_profile, user_profile, animal_and_shell_note):
        carer_user, carer_profile = second_user_profile
        animal, shell = animal_and_shell_note
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=True)
        client.force_login(carer_user)

        response = client.get(f"/note/{animal.id}/{shell.id}/medical_create/")
        assert response.status_code == 200

    @pytest.mark.regression
    def test_post_decimal_weight_is_persisted(self, client, user_profile, animal_and_shell_note):
        """Regression #61: a decimal weight submitted via the view was rejected."""
        owner_user, _ = user_profile
        animal, shell = animal_and_shell_note
        client.force_login(owner_user)

        response = client.post(
            f"/note/{animal.id}/{shell.id}/medical_create/",
            data={
                "record_type": "weight",
                "weight": "4.25",
                "weight_unit_to_present": "kg",
                "height": "",
                "height_unit_to_present": "",
                "custom_name": "",
                "custom_value": "",
                "custom_unit": "",
            },
        )
        assert response.status_code == 302
        assert BiometricWeightRecords.objects.get().weight == Decimal("4.25")

    @pytest.mark.regression
    def test_post_decimal_height_is_persisted(self, client, user_profile, animal_and_shell_note):
        """Regression #61: a decimal height submitted via the view was rejected."""
        owner_user, _ = user_profile
        animal, shell = animal_and_shell_note
        client.force_login(owner_user)

        response = client.post(
            f"/note/{animal.id}/{shell.id}/medical_create/",
            data={
                "record_type": "height",
                "weight": "",
                "weight_unit_to_present": "",
                "height": "31.5",
                "height_unit_to_present": "cm",
                "custom_name": "",
                "custom_value": "",
                "custom_unit": "",
            },
        )
        assert response.status_code == 302
        assert BiometricHeightRecords.objects.get().height == Decimal("31.5")
