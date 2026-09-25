from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ahc.apps.medical_notes.services.notifications import create_email_notification


@pytest.mark.unit
class TestCreateEmailNotificationService:
    """create_email_notification: builds a 7-element bool days array before delegating.

    Uses SimpleNamespace so attribute assignment works without MagicMock interference.
    """

    def _notification_mock(self):
        return MagicMock()

    def test_selected_days_become_true_rest_false(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, ["0", "2", "6"])

        assert form_instance.days_of_week == [True, False, True, False, False, False, True]

    def test_empty_selection_produces_all_false(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, [])

        assert form_instance.days_of_week == [False] * 7

    def test_all_days_selected(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, ["0", "1", "2", "3", "4", "5", "6"])

        assert form_instance.days_of_week == [True] * 7

    def test_related_note_is_set_on_instance(self):
        related_note = MagicMock()
        form_instance = SimpleNamespace()

        with patch("ahc.apps.medical_notes.services.notifications.EmailNotification"):
            create_email_notification(related_note, form_instance, [])

        assert form_instance.related_note is related_note
