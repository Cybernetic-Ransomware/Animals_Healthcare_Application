"""CouchDB attachment client (ADR-08: CouchDB is attachment/file storage only).

All raw pycouchdb interaction is isolated here. Views and other services
interact with CouchDB exclusively through this client.
"""

from __future__ import annotations

from django.conf import settings


class CouchAttachmentClient:
    """Thin adapter over the pycouchdb database object stored in settings.COUCH_DB."""

    def __init__(self, db=None):
        self._db = db or settings.COUCH_DB

    def save_attachment(self, reference_uuid: str, file_name: str, blob: bytes) -> str:
        """Upload a file blob to CouchDB and return the reference UUID (couch_id).

        Creates a CouchDB document keyed by reference_uuid, then attaches the blob.
        """
        self._db.save({"_id": reference_uuid, "name": file_name})
        doc = self._db.get(reference_uuid)
        self._db.put_attachment(doc, blob, filename=file_name)
        return reference_uuid

    def delete_attachment(self, couch_id: str) -> None:
        """Delete the CouchDB document (and its attachment) identified by couch_id."""
        self._db.delete(couch_id)

    def get_attachment(self, reference_id: str) -> tuple[dict, bytes] | None:
        """Retrieve a CouchDB document and its attached file bytes.

        Returns (doc_dict, file_bytes) or None if the document does not exist.
        """
        doc = self._db.get(reference_id)
        if not doc:
            return None
        file_data = self._db.get_attachment(doc, filename=doc.get("name"))
        if not file_data:
            return None
        return doc, file_data
