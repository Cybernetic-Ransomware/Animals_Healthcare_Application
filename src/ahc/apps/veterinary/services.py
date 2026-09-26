from __future__ import annotations

from ahc.apps.veterinary.models import ContactRecord


def create_contact(owner, form) -> ContactRecord:
    """Owner is set on the unsaved instance before save(), so form input can never choose it."""
    record = form.save(commit=False)
    record.owner = owner
    record.save()
    return record


def delete_contact(record: ContactRecord) -> None:
    """Referencing animals keep existing: SET_NULL clears their first-contact FK instead."""
    record.delete()
