from unittest.mock import MagicMock

import pytest

from ahc.apps.medical_notes.services.notes import create_note, next_route_for, update_note


@pytest.mark.unit
class TestNextRouteForService:
    """next_route_for: pure routing logic — no DB, no mocks needed."""

    def test_biometric_event_routes_to_biometric_create(self):
        note = MagicMock()
        note.type_of_event = "biometric_record"
        note.id = "note-uuid"

        url_name, kwargs = next_route_for(note, "animal-uuid")

        assert url_name == "biometric_create"
        assert kwargs == {"pk": "animal-uuid", "note_id": "note-uuid"}

    def test_diet_note_routes_to_feeding_create(self):
        note = MagicMock()
        note.type_of_event = "diet_note"
        note.id = "note-uuid"

        url_name, kwargs = next_route_for(note, "animal-uuid")

        assert url_name == "feeding_create"
        assert kwargs == {"pk": "note-uuid"}

    def test_any_other_type_routes_to_full_timeline(self):
        note = MagicMock()
        note.type_of_event = "general"

        url_name, kwargs = next_route_for(note, "animal-uuid")

        assert url_name == "full_timeline_of_notes"
        assert kwargs == {"pk": "animal-uuid"}


@pytest.mark.unit
class TestCreateNoteService:
    """create_note: sets author/animal on unsaved instance, saves, calls save_m2m."""

    def test_assigns_fields_saves_and_returns_note(self):
        author = MagicMock()
        animal = MagicMock()
        form = MagicMock()
        note_mock = MagicMock()
        form.save.return_value = note_mock

        result = create_note(author, animal, form)

        form.save.assert_called_once_with(commit=False)
        assert note_mock.animal == animal
        assert note_mock.author == author
        note_mock.save.assert_called_once()
        form.save_m2m.assert_called_once()
        assert result is note_mock


@pytest.mark.unit
class TestUpdateNoteService:
    """update_note: conditionally reassigns animal, saves, sets additional_animals."""

    def test_reassigns_animal_when_present_in_cleaned_data(self):
        note = MagicMock()
        form = MagicMock()
        new_animal = MagicMock()
        form.cleaned_data = {"animal": new_animal, "additional_animals": []}

        update_note(note, form)

        assert note.animal == new_animal
        note.save.assert_called_once()

    def test_skips_animal_reassignment_when_not_in_cleaned_data(self):
        note = MagicMock()
        original_animal = note.animal
        form = MagicMock()
        form.cleaned_data = {"additional_animals": []}

        update_note(note, form)

        assert note.animal == original_animal

    def test_sets_additional_animals_m2m(self):
        note = MagicMock()
        form = MagicMock()
        extras = [MagicMock(), MagicMock()]
        form.cleaned_data = {"additional_animals": extras}

        update_note(note, form)

        note.additional_animals.set.assert_called_once_with(extras)
