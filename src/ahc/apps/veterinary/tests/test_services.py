from unittest.mock import MagicMock

import pytest

from ahc.apps.veterinary.services import create_contact, delete_contact


@pytest.mark.unit
class TestCreateContactService:
    """create_contact: sets owner on the unsaved instance before save(); form input can't override it."""

    def test_assigns_owner_saves_and_returns_record(self):
        owner = MagicMock()
        form = MagicMock()
        record_mock = MagicMock()
        form.save.return_value = record_mock

        result = create_contact(owner, form)

        form.save.assert_called_once_with(commit=False)
        assert record_mock.owner == owner
        record_mock.save.assert_called_once()
        assert result is record_mock

    def test_owner_is_assigned_before_save_is_called(self):
        owner = MagicMock()
        form = MagicMock()
        record_mock = MagicMock()
        form.save.return_value = record_mock
        owner_at_save_time = []
        record_mock.save.side_effect = lambda: owner_at_save_time.append(record_mock.owner)

        create_contact(owner, form)

        assert owner_at_save_time == [owner]


@pytest.mark.unit
class TestDeleteContactService:
    def test_deletes_the_record(self):
        record = MagicMock()

        delete_contact(record)

        record.delete.assert_called_once()
