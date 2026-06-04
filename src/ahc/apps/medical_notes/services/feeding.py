"""Service functions for FeedingNote creation and update."""

from __future__ import annotations

from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote


def create_feeding_note(related_note: MedicalRecord, form) -> FeedingNote:
    """Attach a new FeedingNote to its parent MedicalRecord and persist it."""
    feeding_note = form.save(commit=False)
    feeding_note.related_note = related_note
    feeding_note.save()
    return feeding_note
