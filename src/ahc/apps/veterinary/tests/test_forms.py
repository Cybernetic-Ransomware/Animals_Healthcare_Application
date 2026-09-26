import pytest

from ahc.apps.veterinary.forms import MedicalPlaceForm, VetForm


@pytest.mark.unit
class TestVetForm:
    def test_name_is_required(self):
        form = VetForm(data={"name": "", "phone": "", "email": "", "details": ""})

        assert not form.is_valid()
        assert "name" in form.errors

    def test_valid_email_passes(self):
        form = VetForm(data={"name": "Dr Kowalski", "email": "vet@example.com"})

        assert form.is_valid()

    def test_invalid_email_fails(self):
        form = VetForm(data={"name": "Dr Kowalski", "email": "not-an-email"})

        assert not form.is_valid()
        assert "email" in form.errors

    def test_owner_field_is_not_exposed(self):
        form = VetForm()

        assert "owner" not in form.fields

    def test_details_help_text_mentions_vet_contact_access(self):
        form = VetForm()

        assert "vet contact" in form.fields["details"].help_text.lower()

    def test_two_records_with_identical_name_are_both_valid(self):
        first = VetForm(data={"name": "Dr Kowalski"})
        second = VetForm(data={"name": "Dr Kowalski"})

        assert first.is_valid()
        assert second.is_valid()

    def test_owner_kwarg_is_accepted_and_stored(self):
        owner = object()

        form = VetForm(owner=owner)

        assert form.owner is owner


@pytest.mark.unit
class TestMedicalPlaceForm:
    def test_name_is_required(self):
        form = MedicalPlaceForm(data={"name": ""})

        assert not form.is_valid()
        assert "name" in form.errors

    def test_valid_email_passes(self):
        form = MedicalPlaceForm(data={"name": "City Vet Clinic", "email": "clinic@example.com"})

        assert form.is_valid()

    def test_invalid_email_fails(self):
        form = MedicalPlaceForm(data={"name": "City Vet Clinic", "email": "not-an-email"})

        assert not form.is_valid()
        assert "email" in form.errors

    def test_valid_website_passes(self):
        form = MedicalPlaceForm(data={"name": "City Vet Clinic", "website": "https://example.com"})

        assert form.is_valid()

    def test_invalid_website_fails(self):
        form = MedicalPlaceForm(data={"name": "City Vet Clinic", "website": "not-a-url"})

        assert not form.is_valid()
        assert "website" in form.errors

    def test_owner_field_is_not_exposed(self):
        form = MedicalPlaceForm()

        assert "owner" not in form.fields

    def test_details_help_text_mentions_vet_contact_access(self):
        form = MedicalPlaceForm()

        assert "vet contact" in form.fields["details"].help_text.lower()

    def test_two_records_with_identical_name_are_both_valid(self):
        first = MedicalPlaceForm(data={"name": "City Vet Clinic"})
        second = MedicalPlaceForm(data={"name": "City Vet Clinic"})

        assert first.is_valid()
        assert second.is_valid()
