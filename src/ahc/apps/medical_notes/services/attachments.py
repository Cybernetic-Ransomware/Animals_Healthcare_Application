"""Services for MedicalRecordAttachment: upload, delete, download via CouchDB."""

from __future__ import annotations

from django.conf import settings
from django.db import transaction

from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment
from ahc.apps.medical_notes.services.couch import CouchAttachmentClient


class AttachmentLimitExceeded(Exception):
    """Raised when the per-note attachment limit (COUCH_DB_LIMIT_PER_NOTE) is reached."""


def upload_attachment(
    medical_record: MedicalRecord,
    attachment_instance: MedicalRecordAttachment,
    uploaded_file,
    couch_client: CouchAttachmentClient | None = None,
) -> MedicalRecordAttachment:
    """Upload a file to CouchDB and persist the attachment metadata to PostgreSQL.

    Raises AttachmentLimitExceeded when the per-note limit is already reached.
    The caller is responsible for form validation; this function operates on
    already-validated data.
    """
    if couch_client is None:
        couch_client = CouchAttachmentClient()

    limit = settings.COUCH_DB_LIMIT_PER_NOTE
    current_count = MedicalRecordAttachment.objects.filter(medical_record=medical_record).count()
    if current_count >= limit:
        raise AttachmentLimitExceeded(f"Maximum of {limit} attachments per note already reached.")

    reference_uuid = str(attachment_instance.id)
    file_name = uploaded_file.name
    uploaded_file.seek(0)
    blob = uploaded_file.read()

    with transaction.atomic():
        couch_client.save_attachment(reference_uuid, file_name, blob)
        attachment_instance.medical_record = medical_record
        attachment_instance.file_name = file_name
        attachment_instance.couch_id = reference_uuid
        attachment_instance.file = None
        attachment_instance.save()

    return attachment_instance


def delete_attachment(
    attachment: MedicalRecordAttachment,
    couch_client: CouchAttachmentClient | None = None,
) -> None:
    """Remove the attachment from CouchDB and delete its PostgreSQL row."""
    if couch_client is None:
        couch_client = CouchAttachmentClient()

    couch_client.delete_attachment(str(attachment.couch_id))
    attachment.delete()


def download_attachment(
    couch_id: str,
    couch_client: CouchAttachmentClient | None = None,
) -> tuple[bytes, str]:
    """Retrieve attachment bytes and file name from CouchDB.

    Returns (file_bytes, file_name).
    Raises django.http.Http404 when the document or its blob is missing.
    """
    from django.http import Http404

    if couch_client is None:
        couch_client = CouchAttachmentClient()

    result = couch_client.get_attachment(couch_id)
    if result is None:
        raise Http404("Attachment not found.")

    doc, file_data = result
    return file_data, doc.get("name", "")
