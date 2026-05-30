"""Read-only selectors for the medical_notes app.

All functions are side-effect free: they only query the database and return
values. Views, services, and mixins should call these instead of writing
inline ORM queries.
"""

from __future__ import annotations

from django.db.models import QuerySet

from ahc.apps.animals.selectors import animals_visible_to, user_can_access_animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment


def animal_choices_for(profile, exclude_id=None) -> list[tuple]:
    """Return (id, full_name) pairs for animals accessible to the profile.

    Optionally excludes one animal by UUID (used when the animal is already
    the primary animal on a note).
    """
    queryset = animals_visible_to(profile)
    if exclude_id is not None:
        queryset = queryset.exclude(id=exclude_id)
    return [(animal.id, animal.full_name) for animal in queryset]


def timeline_for(
    animal,
    type_of_event: str | None = None,
    tag_name: str | None = None,
) -> QuerySet[MedicalRecord]:
    """Return MedicalRecords for an animal, optionally filtered by type or tag.

    Results are prefetch_related for attachments. Ordering and timezone
    localisation remain the caller's responsibility (presentation logic).
    """
    queryset = MedicalRecord.objects.filter(animal=animal).prefetch_related("attachments")
    if type_of_event:
        queryset = queryset.filter(type_of_event=type_of_event)
    if tag_name:
        queryset = queryset.filter(note_tags__slug=tag_name)
    return queryset


def feeding_notes_for(medical_record) -> QuerySet:
    """Return all FeedingNotes linked to the given MedicalRecord."""
    from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote

    return FeedingNote.objects.filter(related_note=medical_record)


def notifications_for_feednote(feednote_pk) -> QuerySet:
    """Return EmailNotifications linked to a specific FeedingNote PK."""
    from ahc.apps.medical_notes.models.type_feeding_notes import EmailNotification

    return EmailNotification.objects.filter(related_note=feednote_pk)


def notifications_for_mednote(mednote_uuid) -> QuerySet:
    """Return EmailNotifications reachable through FeedingNotes of a MedicalRecord."""
    from ahc.apps.medical_notes.models.type_feeding_notes import EmailNotification, FeedingNote

    feednotes = FeedingNote.objects.filter(related_note=mednote_uuid)
    return EmailNotification.objects.filter(related_note__in=feednotes).order_by("-last_modification")


def is_note_author(profile, note: MedicalRecord) -> bool:
    """Return True if the profile is the author of the note."""
    return note.author == profile


def is_attachment_author(profile, attachment: MedicalRecordAttachment) -> bool:
    """Return True if the profile authored the note that owns this attachment."""
    return attachment.medical_record.author == profile


def can_access_note_animal(profile, note: MedicalRecord) -> bool:
    """Return True if the profile is owner or keeper of the animal linked to the note."""
    return user_can_access_animal(profile, note.animal)
