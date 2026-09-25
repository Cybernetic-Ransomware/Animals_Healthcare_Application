from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.http import Http404

from ahc.apps.medical_notes.services.attachments import (
    AttachmentLimitExceeded,
    delete_attachment,
    download_attachment,
    upload_attachment,
)


def _make_couch_client(save_ok=True, get_result=None, delete_ok=True):
    """Build a mock CouchAttachmentClient for attachment service tests."""
    client = MagicMock()
    client.save_attachment.return_value = "ref-uuid"
    client.delete_attachment.return_value = None
    client.get_attachment.return_value = get_result
    return client


@pytest.mark.unit
class TestUploadAttachmentService:
    """upload_attachment: orchestrates limit check, CouchDB write, and model save."""

    def test_raises_when_limit_reached(self):
        medical_record = MagicMock()
        attachment = MagicMock()
        uploaded_file = BytesIO(b"data")
        uploaded_file.name = "photo.jpg"
        client = _make_couch_client()

        with (
            patch("ahc.apps.medical_notes.services.attachments.MedicalRecordAttachment.objects.filter") as mock_filter,
            patch("ahc.apps.medical_notes.services.attachments.settings") as mock_settings,
        ):
            mock_settings.COUCH_DB_LIMIT_PER_NOTE = 5
            mock_filter.return_value.count.return_value = 5

            with pytest.raises(AttachmentLimitExceeded):
                upload_attachment(medical_record, attachment, uploaded_file, couch_client=client)

        client.save_attachment.assert_not_called()

    def test_saves_to_couch_and_model_when_under_limit(self):
        medical_record = MagicMock()
        attachment = MagicMock()
        attachment.id = "test-uuid"
        uploaded_file = BytesIO(b"image-data")
        uploaded_file.name = "photo.jpg"
        client = _make_couch_client()

        with (
            patch("ahc.apps.medical_notes.services.attachments.MedicalRecordAttachment.objects.filter") as mock_filter,
            patch("ahc.apps.medical_notes.services.attachments.settings") as mock_settings,
            patch("ahc.apps.medical_notes.services.attachments.transaction"),
        ):
            mock_settings.COUCH_DB_LIMIT_PER_NOTE = 5
            mock_filter.return_value.count.return_value = 2

            result = upload_attachment(medical_record, attachment, uploaded_file, couch_client=client)

        client.save_attachment.assert_called_once_with("test-uuid", "photo.jpg", b"image-data")
        assert attachment.couch_id == "test-uuid"
        assert attachment.file_name == "photo.jpg"
        assert attachment.file is None
        assert result is attachment


@pytest.mark.unit
class TestDeleteAttachmentService:
    """delete_attachment: calls couch client then deletes the model row."""

    def test_deletes_from_couch_and_db(self):
        attachment = MagicMock()
        attachment.couch_id = "some-couch-id"
        client = _make_couch_client()

        delete_attachment(attachment, couch_client=client)

        client.delete_attachment.assert_called_once_with("some-couch-id")
        attachment.delete.assert_called_once()


@pytest.mark.unit
class TestDownloadAttachmentService:
    """download_attachment: retrieves bytes from couch client; raises Http404 on missing."""

    def test_returns_bytes_and_name(self):
        client = _make_couch_client(get_result=({"name": "report.pdf"}, b"pdf-bytes"))

        file_data, file_name = download_attachment("ref-uuid", couch_client=client)

        assert file_data == b"pdf-bytes"
        assert file_name == "report.pdf"
        client.get_attachment.assert_called_once_with("ref-uuid")

    def test_raises_http404_when_not_found(self):
        client = _make_couch_client(get_result=None)

        with pytest.raises(Http404):
            download_attachment("missing-id", couch_client=client)
