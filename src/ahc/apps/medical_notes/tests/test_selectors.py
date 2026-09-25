from unittest.mock import MagicMock, patch

import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.medical_notes.selectors import (
    can_access_note_animal,
    is_attachment_author,
    is_author_of_any_note,
    is_note_author,
)


@pytest.mark.unit
class TestMedicalNoteSelectors:
    """Pure predicate selectors — no DB, MagicMock only."""

    def test_is_note_author_true_for_author(self):
        profile = MagicMock()
        note = MagicMock()
        note.author = profile
        assert is_note_author(profile, note) is True

    def test_is_note_author_false_for_non_author(self):
        note = MagicMock()
        note.author = MagicMock()
        assert is_note_author(MagicMock(), note) is False

    def test_is_attachment_author_true_when_note_author_matches(self):
        profile = MagicMock()
        attachment = MagicMock()
        attachment.medical_record.author = profile
        assert is_attachment_author(profile, attachment) is True

    def test_is_attachment_author_false_for_other_profile(self):
        attachment = MagicMock()
        attachment.medical_record.author = MagicMock()
        assert is_attachment_author(MagicMock(), attachment) is False

    def test_can_access_note_animal_delegates_to_modify_predicate(self):
        profile = MagicMock()
        note = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.user_can_modify_animal", return_value=True) as mock_selector:
            result = can_access_note_animal(profile, note)

        mock_selector.assert_called_once_with(profile, note.animal)
        assert result is True

    def test_can_access_note_animal_returns_false_when_denied(self):
        profile = MagicMock()
        note = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.user_can_modify_animal", return_value=False):
            assert can_access_note_animal(profile, note) is False


@pytest.mark.unit
class TestVaccinationSelectors:
    """due_vaccination_reminders: pure filtering logic verified with MagicMock."""

    def test_other_history_for_excludes_vaccination_note(self):
        from unittest.mock import patch

        from ahc.apps.medical_notes.selectors import other_history_for

        animal = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.MedicalRecord") as MockRecord:
            qs = MagicMock()
            MockRecord.objects.filter.return_value = qs
            qs.exclude.return_value = qs
            qs.prefetch_related.return_value = qs
            qs.order_by.return_value = qs

            other_history_for(animal)

            exclude_call = qs.exclude.call_args
            excluded_types = exclude_call[1]["type_of_event__in"]
            assert "vaccination_note" in excluded_types

    def test_other_records_for_excludes_vaccination_note(self):
        from ahc.apps.medical_notes.selectors import other_records_for

        animal = MagicMock()
        with patch("ahc.apps.medical_notes.selectors.MedicalRecord") as MockRecord:
            qs = MagicMock()
            MockRecord.objects.filter.return_value = qs
            qs.exclude.return_value = qs
            qs.prefetch_related.return_value = qs
            qs.order_by.return_value = qs

            other_records_for(animal)

            exclude_call = qs.exclude.call_args
            excluded_types = exclude_call[1]["type_of_event__in"]
            assert "vaccination_note" in excluded_types


@pytest.mark.integration
@pytest.mark.django_db
class TestIsAuthorOfAnyNote:
    def test_true_when_profile_has_authored_a_note(self, diet_note_shell, user_profile):
        _, profile = user_profile
        assert is_author_of_any_note(profile) is True

    def test_false_for_profile_with_no_notes(self, db, second_user_profile):
        _, other_profile = second_user_profile
        assert is_author_of_any_note(other_profile) is False


@pytest.mark.integration
@pytest.mark.django_db
class TestOtherRecordsForSelector:
    """other_records_for: excludes medical_visit and diet_note types."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Buddy", owner=profile)

    def test_excludes_medical_visit_and_diet_note(self, animal, user_profile):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.selectors import other_records_for

        _, profile = user_profile
        MedicalRecord.objects.create(
            animal=animal, author=profile, short_description="Visit", type_of_event="medical_visit"
        )
        MedicalRecord.objects.create(animal=animal, author=profile, short_description="Diet", type_of_event="diet_note")
        note = MedicalRecord.objects.create(
            animal=animal, author=profile, short_description="Other", type_of_event="fast_note"
        )

        results = list(other_records_for(animal))
        ids = [r.id for r in results]
        assert note.id in ids
        assert len(results) == 1

    def test_returns_empty_when_only_special_types(self, animal, user_profile):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.selectors import other_records_for

        _, profile = user_profile
        MedicalRecord.objects.create(animal=animal, author=profile, short_description="V", type_of_event="medical_visit")
        assert list(other_records_for(animal)) == []
