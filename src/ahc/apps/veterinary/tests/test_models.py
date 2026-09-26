import pytest

from ahc.apps.veterinary.models import MedicalPlace, Vet


@pytest.mark.unit
class TestAsContactText:
    def test_name_only(self):
        vet = Vet(name="Dr Kowalski")
        assert vet.as_contact_text() == "Dr Kowalski"

    def test_skips_empty_phone_and_email(self):
        vet = Vet(name="Dr Kowalski", phone="", email="")
        assert vet.as_contact_text() == "Dr Kowalski"

    def test_skips_empty_address_and_website_on_medical_place(self):
        place = MedicalPlace(name="City Vet Clinic", address="", website="")
        assert place.as_contact_text() == "City Vet Clinic"

    def test_field_order(self):
        place = MedicalPlace(
            name="City Vet Clinic",
            phone="123-456-789",
            email="contact@example.com",
            address="Main St 1",
            website="https://example.com",
        )
        assert place.as_contact_text() == (
            "City Vet Clinic\n123-456-789\ncontact@example.com\nMain St 1\nhttps://example.com"
        )

    def test_details_appended_verbatim(self):
        vet = Vet(name="Dr Kowalski", phone="123", details="\ntylko nagłe przypadki")
        assert vet.as_contact_text() == "Dr Kowalski\n123\n\ntylko nagłe przypadki"

    def test_leading_blank_line_in_details_is_preserved(self):
        vet = Vet(name="Dr Kowalski", details="\n\nline after two blank lines")
        assert vet.as_contact_text() == "Dr Kowalski\n\n\nline after two blank lines"

    def test_name_at_max_length(self):
        name = "a" * 250
        vet = Vet(name=name)
        assert vet.as_contact_text() == name

    def test_polish_characters(self):
        vet = Vet(name="Żółw Ćma Świnka")
        assert vet.as_contact_text() == "Żółw Ćma Świnka"

    def test_emoji(self):
        vet = Vet(name="Dr Kowalski \U0001f43e")
        assert vet.as_contact_text() == "Dr Kowalski \U0001f43e"


@pytest.mark.integration
@pytest.mark.django_db
class TestContactRecordPersistence:
    def test_vet_can_be_saved(self, user_profile):
        _, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        assert Vet.objects.filter(pk=vet.pk).exists()

    def test_medical_place_can_be_saved(self, user_profile):
        _, profile = user_profile
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        assert MedicalPlace.objects.filter(pk=place.pk).exists()

    def test_deleting_profile_cascades_to_vets_and_medical_places(self, user_profile):
        _, profile = user_profile
        Vet.objects.create(name="Dr Kowalski", owner=profile)
        MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)

        profile.delete()

        assert Vet.objects.count() == 0
        assert MedicalPlace.objects.count() == 0

    def test_same_owner_can_have_two_contacts_with_identical_name(self, user_profile):
        _, profile = user_profile
        Vet.objects.create(name="Dr Kowalski", owner=profile)
        Vet.objects.create(name="Dr Kowalski", owner=profile)

        assert Vet.objects.filter(name="Dr Kowalski", owner=profile).count() == 2
