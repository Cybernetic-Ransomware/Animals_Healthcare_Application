"""CouchDB attachment client (ADR-08: CouchDB is attachment/file storage only).

All raw HTTP interaction with CouchDB is isolated here. Views and other services
interact with CouchDB exclusively through this client.
"""

from __future__ import annotations

import urllib.parse

import requests
from django.conf import settings


class CouchAttachmentClient:
    """Thin HTTP adapter over the CouchDB REST API.

    Reads connection parameters from ``settings.COUCHDB_*`` at instantiation
    time. Pass explicit constructor arguments in tests to avoid touching Django
    settings.
    """

    def __init__(
        self,
        base_url: str | None = None,
        db_name: str | None = None,
        auth: tuple[str, str] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = (base_url or settings.COUCHDB_BASE_URL).rstrip("/")
        self._db_name = db_name or settings.COUCHDB_DB_NAME
        self._auth = auth or (settings.COUCHDB_USER, settings.COUCHDB_PASSWORD)
        self._session = session or requests.Session()

    def _doc_url(self, doc_id: str) -> str:
        return f"{self._base_url}/{self._db_name}/{urllib.parse.quote(doc_id, safe='')}"

    def save_attachment(self, reference_uuid: str, file_name: str, blob: bytes) -> str:
        """Upload a file blob to CouchDB and return the reference UUID (couch_id).

        Creates a CouchDB document keyed by reference_uuid, then attaches the blob.
        """
        r = self._session.put(self._doc_url(reference_uuid), json={"name": file_name}, auth=self._auth)
        r.raise_for_status()
        rev = r.json()["rev"]

        att_url = f"{self._doc_url(reference_uuid)}/{urllib.parse.quote(file_name, safe='')}?rev={rev}"
        r2 = self._session.put(
            att_url,
            data=blob,
            auth=self._auth,
            headers={"Content-Type": "application/octet-stream"},
        )
        r2.raise_for_status()
        return reference_uuid

    def delete_attachment(self, couch_id: str) -> None:
        """Delete the CouchDB document (and its attachment) identified by couch_id."""
        r = self._session.get(self._doc_url(couch_id), auth=self._auth)
        if r.status_code == 404:
            return
        r.raise_for_status()
        rev = r.json()["_rev"]

        d = self._session.delete(f"{self._doc_url(couch_id)}?rev={rev}", auth=self._auth)
        d.raise_for_status()

    def get_attachment(self, reference_id: str) -> tuple[dict, bytes] | None:
        """Retrieve a CouchDB document and its attached file bytes.

        Returns (doc_dict, file_bytes) or None if the document does not exist.
        """
        r = self._session.get(self._doc_url(reference_id), auth=self._auth)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        doc = r.json()

        name = doc.get("name")
        a = self._session.get(
            f"{self._doc_url(reference_id)}/{urllib.parse.quote(name, safe='')}",
            auth=self._auth,
        )
        if a.status_code == 404:
            return None
        a.raise_for_status()
        return doc, a.content
